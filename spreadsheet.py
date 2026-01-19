"""Google Sheets操作"""
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)


class SpreadsheetWriter:
    """Google Sheetsへのデータ書き込みクラス"""
    
    def __init__(self, credentials_path="credentials.json"):
        self.credentials_path = credentials_path
        self.client = None
    
    def authenticate(self):
        """Google Sheetsの認証"""
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_path, scope
            )
            self.client = gspread.authorize(creds)
            logger.info("Google Sheets認証に成功しました")
        except FileNotFoundError:
            logger.error(f"{self.credentials_path} が見つかりません")
            raise
        except gspread.exceptions.AuthenticationError:
            logger.error("Google Sheets認証エラー: 認証情報が無効です")
            raise
    
    def write_to_spreadsheet(self, data, spreadsheet_url, sheet_name="団員管理", event_number=None):
        """スプレッドシートにデータを書き込む"""
        try:
            if self.client is None:
                self.authenticate()
            
            # シート取得
            sheet = self.client.open_by_url(spreadsheet_url).worksheet(sheet_name)
            logger.info(f"シートを開きました: {sheet_name}")

            # 名前一覧（B列）を取得（1行目はヘッダー）
            name_cells = sheet.col_values(2)
            name_list = [name.strip() for name in name_cells[1:]]  # indexは2行目から

            # 新しい順位列の挿入（C列に挿入 → 既存列が右にずれる）
            new_col_title = f"第{event_number}回"
            sheet.insert_cols([[new_col_title] + [""] * len(name_list)], col=3)
            logger.info(f"新しい列を追加しました: {new_col_title}")

            # データの書き込み
            for name, rank in data:
                name = name.strip()
                if name in name_list:
                    row_index = name_list.index(name) + 2  # 1ベース + ヘッダー
                    sheet.update_cell(row_index, 3, rank)
                else:
                    # 新規団員の行を末尾に追加
                    new_row_index = len(name_list) + 2
                    sheet.update_cell(new_row_index, 2, name)  # 名前（B列）
                    sheet.update_cell(new_row_index, 3, rank)  # 新しい順位（C列）
                    name_list.append(name)
            
            logger.info(f"{len(data)}件のデータを書き込みしました")
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"スプレッドシートが見つかりません: {spreadsheet_url}")
            raise
        except Exception as e:
            logger.error(f"スプレッドシート書き込みエラー: {e}")
            raise
