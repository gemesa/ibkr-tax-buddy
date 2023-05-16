import argparse
import datetime
import mnb
import PyPDF2
import re
import time
from typing import Dict, List, Tuple


def parse_pdf() -> Tuple[List, List]:
    tax = []
    div = []

    with open(args.input[0], "rb") as f:
        reader = PyPDF2.PdfReader(f)

        for i in range(args.pages[0], args.pages[-1]):
            page = reader.pages[i]

            text = page.extract_text()

            # regex has to match the following:
            # 2022-01-14 NFG(US6361801011) Cash Dividend USD 0.455 per Share - US Tax -0.34
            #
            # 2022-01-18CAH(US14149Y1082) Cash Dividend USD 0.4908 per Share - US
            # Tax-0.59
            #
            # 2022-03-01 ENB (CA29250N1050) Cash Dividend USD 0.675993 - CA Tax -1.42
            match = re.findall(rf"(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+).+(?:US|CA)\n* *Tax *(?P<tax>-*\d+\.\d+)", text)
            if not match and args.verbose:
                print(f"tax regex error on page {i}")
            tax += match

            # # regex has to match the following:
            # 2022-03-15ED(US2091151041) Cash Dividend USD 0.79 per Share
            # (Ordinary Dividend)6.32
            #
            # 2022-05-13MMP(US5590801065) Cash Dividend USD 1.0375 per Share
            # (Limited Partnership)9.34
            #
            # 2022-08-30ETD(US2976021046) Cash Dividend USD 0.50 per Share
            # (Bonus Dividend)24.00
            match = re.findall(rf"(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+).+\n*\((?:Ordinary|Limited|Bonus)\n* *(?:Dividend|Partnership)\)(?P<div>-*\d+\.\d+)", text)
            if not match and args.verbose:
                print(f"div regex error on page {i}")
            div += match
    return tax, div


def filter_by_year(data_raw: List) -> List:
    data_filtered = [data for data in data_raw if int(data[0]) == args.year[0]]
    return data_filtered


def calc_totals(data_raw: List) -> Dict:
    totals = {"usd": 0.0, "huf": 0.0}

    for data in data_raw:
        year = int(data[0])
        month = int(data[1])
        day = int(data[2])
        usd = float(data[3])
        totals["usd"] += usd
        exchange_rate = []
        while not exchange_rate:
            exchange_rate = client.get_exchange_rates(datetime.date(year, month, day), datetime.date(year, month, day), ["USD"])
            if not exchange_rate:
                if args.verbose:
                    print(f"exchange rate error - {year}-{month}-{day}, trying again with - {year}-{month}-{day + 1}")
                day += 1
        uds2huf_rate = exchange_rate[0].rates[0].rate
        totals["huf"] += usd * uds2huf_rate
        time.sleep(0.1)
    return totals


if __name__ == "__main__":
    client = mnb.Mnb()

    parser = argparse.ArgumentParser(description="IBKR tax and dividend helper")
    parser.add_argument("-i", "--input", type=str, nargs=1, required=True, help="input statement (.pdf)")
    parser.add_argument("-p", "--pages", type=int, nargs="+", required=True,
                        help="start and end pages of tax and dividend info")
    parser.add_argument("-y", "--year", type=int, nargs=1, required=True, help="year filter")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose mode")
    args = parser.parse_args()

    print("Parsing pdf...")
    tax, div = parse_pdf()
    tax = filter_by_year(tax)
    div = filter_by_year(div)
    print("Calculating tax totals...")
    totals = calc_totals(tax)
    print(f"tax [USD]: {totals['usd']}")
    print(f"tax [HUF]: {totals['huf']}")
    print(f"# of tax transactions: {len(tax)}")
    print("Calculating div totals...")
    totals = calc_totals(div)
    print(f"div [USD]: {totals['usd']}")
    print(f"div [HUF]: {totals['huf']}")
    print(f"# of div transactions: {len(div)}")
