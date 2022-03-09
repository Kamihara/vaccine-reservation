from sys import float_repr_style
from typing import Dict
from typing_extensions import ParamSpec
from black import TargetVersion
import requests
import json
from time import sleep
import datetime
import os
from dotenv import load_dotenv
import argparse
from collections import namedtuple

load_dotenv()

VACCINE_MAPPING = (
    ("Pfizer", 1),
    ("AstraZeneca", 2),
    ("Moderna", 3),
    ("Pfizer(for child)", 4),
)


class Client(object):
    def __init__(
        self,
        partition_key,
        card_no,
        password,
        access_token=None,
        target_date=None,
        target_vaccine=None,
    ) -> None:
        self.partition_key = partition_key
        self.card_no = card_no
        self.password = password
        self.access_token = access_token
        self.target_date = target_date
        self.target_vaccine = target_vaccine

    def login(self) -> Dict:
        url = f"https://api.vaccines.sciseed.jp/public/{self.partition_key}/login/"
        payload = {
            "partition_key": self.partition_key,
            "range_key": self.card_no,
            "password": self.password,
        }
        res = requests.post(url=url, data=payload)
        c.access_token = json.loads(res.content)["access"]
        return

    def get_available_department(self) -> Dict:
        url = f"https://api-cache.vaccines.sciseed.jp/public/{self.partition_key}/available_department/"
        res = requests.get(url=url)
        return json.loads(res.content)

    def get_department(self, department_id) -> Dict:
        url = f"https://api-cache.vaccines.sciseed.jp/public/{self.partition_key}/department/{department_id}"
        res = requests.get(url=url)
        return json.loads(res.content)

    def get_available_date(self, department_id, item_id, year, month) -> Dict:
        url = f"https://api-cache.vaccines.sciseed.jp/public/{self.partition_key}/available_date/?department_id={department_id}&item_id={item_id}&year={year}&month={month}"
        res = requests.get(url=url)
        return json.loads(res.content)

    def get_reservation_frame(self, department_id, item_id, date) -> Dict:
        url = f"https://api-cache.vaccines.sciseed.jp/public/{self.partition_key}/reservation_frame/?department_id={department_id}&item_id={item_id}&start_date_after={date}&start_date_before={date}"
        res = requests.get(url=url)
        return json.loads(res.content)

    def get_reservation_frame_without_dept(self, item_id, date) -> Dict:
        url = f"https://api-cache.vaccines.sciseed.jp/public/{self.partition_key}/reservation_frame/?item_id={item_id}&start_date_after={date}&start_date_before={date}"
        res = requests.get(url=url)
        return json.loads(res.content)

    def reserve(self, frame_id, access_token):
        url = (
            f"https://api.vaccines.sciseed.jp/public/{self.partition_key}/reservation/"
        )
        authorization_header = f"Bearer {access_token}"
        headers = {"authorization": authorization_header}
        payload = {"reservation_frame_id": frame_id}
        res = requests.post(url=url, headers=headers, data=payload)
        return res


def get_vaccine_dict():
    d = {}
    for k, v in VACCINE_MAPPING:
        d[k] = v
    return d


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="To get vaccine reservation")
    parser.add_argument("--by_date", action="store_true", default=False)
    parser.add_argument("--by_dept", action="store_true", default=False)
    args = parser.parse_args()

    c = Client(
        partition_key=os.getenv("PARTITION_KEY"),
        card_no=os.getenv("CARD_NO"),
        password=os.getenv("PASSWORD"),
        target_date=os.getenv("TARGET_DATE"),
        target_vaccine=os.getenv("TARGET_VACCINE"),
    )
    c.login()
    loop_times = 0
    end_flag = False
    month = datetime.datetime.now().month

    if args.by_dept:
        while end_flag == False:
            available_department = None
            while True:
                loop_times += 1
                print(f"get available department: {loop_times} times")
                available_department = c.get_available_department()
                if available_department["department_list"]:
                    break
                sleep(5)

            department_info = {}
            for id in available_department["department_list"]:
                department_info = c.get_department(department_id=id)
                item_id = department_info["item"][0]

                available_dates = dict()
                for delta in (0, 1, 2):
                    target_month = month + delta
                    available_dates.update(
                        c.get_available_date(
                            department_id=id,
                            item_id=item_id,
                            year=2021,
                            month=target_month,
                        )
                    )

                for date, status in available_dates.items():
                    reservation_frame_list = []
                    if status["available"]:
                        print(f"date: {date}, status: {status}")
                        reservation_frame_list = c.get_reservation_frame(
                            department_id=id, item_id=item_id, date=date
                        )["reservation_frame"]
                    for frame in reservation_frame_list:
                        print(frame)
                        if (
                            frame["reservation_cnt_limit"] - frame["reservation_cnt"]
                            > 0
                        ):
                            res = c.reserve(
                                frame_id=frame["id"], access_token=c.access_token
                            )
                            print(res.content)
                            if json.loads(res.content).get("reservation"):
                                print(f"finished!")
                                end_flag = True
                                break

    if args.by_date:
        VACCINE_DICT = get_vaccine_dict()
        print(VACCINE_DICT)
        print(c.target_vaccine)
        item_id = VACCINE_DICT[c.target_vaccine]
        while end_flag == False:
            reservation_frame_list = c.get_reservation_frame_without_dept(
                item_id=item_id, date=c.target_date
            )["reservation_frame"]
            for frame in reservation_frame_list:
                print(frame)
                if frame["reservation_cnt_limit"] - frame["reservation_cnt"] > 0:
                    res = c.reserve(frame_id=frame["id"], access_token=c.access_token)
                    print(res.content)
                    if json.loads(res.content).get("reservation"):
                        print(f"finished!")
                        end_flag = True
                        break
