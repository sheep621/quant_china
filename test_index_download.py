import baostock as bs
import pandas as pd

def test_index_download(code):
    bs.login()
    print(f"Testing download for {code}...")
    
    # 指数数据字段通常没有 turn, isST 等，但我们可以先试一下通用的
    fields = "date,code,open,high,low,close,volume,amount,pctChg"
    
    rs = bs.query_history_k_data_plus(code,
        fields,
        start_date='2024-01-01', end_date='2024-03-20',
        frequency="d", adjustflag="3") # 指数通常用不复权
    
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    
    bs.logout()
    
    if data_list:
        df = pd.DataFrame(data_list, columns=rs.fields)
        print(f"Successfully downloaded {len(df)} rows for {code}")
        print(df.head())
        return True
    else:
        print(f"Failed to download data for {code}: {rs.error_msg}")
        return False

if __name__ == "__main__":
    test_index_download("sh.000300")
    test_index_download("sh.000905")
