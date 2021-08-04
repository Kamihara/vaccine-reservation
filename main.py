from sys import float_repr_style
from typing import Dict
from typing_extensions import ParamSpec
import requests
import json
from time import sleep
import datetime
import os
from dotenv import load_dotenv

load_dotenv()


class Client(object):
    def __init__(self, partition_key, card_no, password) -> None:
        self.partition_key = partition_key
        self.card_no = card_no
        self.password = password

    def login(self) -> Dict:
        url = f"https://api.vaccines.sciseed.jp/public/{self.partition_key}/login/"
        payload = {
            "partition_key": self.partition_key,
            "range_key": self.card_no,
            "password": self.password,
        }
        res = requests.post(url=url, data=payload)
        return json.loads(res.content)

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

    def reserve(self, frame_id, access_token):
        url = (
            f"https://api.vaccines.sciseed.jp/public/{self.partition_key}/reservation/"
        )
        authorization_header = f"Bearer {access_token}"
        headers = {"authorization": authorization_header}
        payload = {"reservation_frame_id": frame_id}
        res = requests.post(url=url, headers=headers, data=payload)
        return res


if __name__ == "__main__":
    c = Client(
        partition_key=os.getenv("PARTITION_KEY"),
        card_no=os.getenv("CARD_NO"),
        password=os.getenv("PASSWORD"),
    )
    login_result = c.login()
    print(login_result)
    access_token = login_result["access"]
    loop_times = 0
    end_flag = False
    month = datetime.datetime.now().month

    while end_flag == False:
        available_department = None
        while True:
            loop_times += 1
            print(f"get available department: {loop_times} times")
            available_department = c.get_available_department()
            if available_department["department_list"]:
                break
            sleep(5)
        print(f'available department: {available_department["department_list"]}')

        department_info = dict()
        for id in available_department["department_list"]:
            department_info = c.get_department(department_id=id)
            item_id = department_info["item"][0]

            available_dates = dict()
            for delta in (0, 1, 2):
                target_month = month + delta
                available_dates.update(
                    c.get_available_date(
                        department_id=id, item_id=item_id, year=2021, month=target_month
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
                    if frame["reservation_cnt_limit"] - frame["reservation_cnt"] > 0:
                        res = c.reserve(frame_id=frame["id"], access_token=access_token)
                        print(res.content)
                        if json.loads(res.content).get("reservation"):
                            print(f"finished!")
                            end_flag = True
                            break
