# vaccine-reservation

ワクチン接種予約取得のためのスクリプト

1. このリポジトリをcloneする。
2. `.env` ファイルを作成する。
```sh
PARTITION_KEY=自治体に応じたキー
CARD_NO=接種券番号
PASSWORD=摂取予約サイトのパスワード
```
3. python実行環境をpipenvで構築
```sh
$ pipenv shell
```
4. 実行
```sh
$ python main.py
```