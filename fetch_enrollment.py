#! /usr/bin/env python3
"""
fetch_enrollment.py
Script to fetch enrollment numbers for U Utah astro classes
Project website: https://github.com/utah-astro/enrollment

Requires Python 3.7+, requests, beautifulsoup4, lxml, astropy

The MIT License (MIT)
Copyright (c) 2022 Yao-Yuan Mao (yymao)
http://opensource.org/licenses/MIT
"""

import time
import argparse
import requests
from bs4 import BeautifulSoup
from astropy.table import Table, join, vstack

__author__ = "Yao-Yuan Mao"
__version__ = "0.1.0"


def term_key_to_semester_year(term_key):
    """
    Convert a 4-digit term number to semester and year
    """
    term_key = int(term_key)
    return ["Spring", "Summer", "Fall"][term_key % 10 // 2 - 2], 2000 + term_key % 1000 // 10


def semester_year_to_term_key(semester, year):
    """
    Convert semester and year to a 4-digit term number

    """
    semester = str(semester).strip().lower()
    return 1000 + int(year) % 100 * 10 + ["spring", "summer", "fall"].index(semester) * 2 + 4


def fetch_classes(term_key, subject):
    """
    Fetch the classes for a specific term and subject.
    Returns an iterator of dictionaries. 
    To convert the returned values to an astropy table, use:
    `Table(rows=fetch_classes(term_key, subject))`
    """
    subject = str(subject).strip().upper()
    source = requests.get(f"https://student.apps.utah.edu/uofu/stu/ClassSchedules/main/{term_key}/seating_availability.html?subject={subject}").content
    soup = BeautifulSoup(source, "lxml")
    for row in soup.find(id="seatingAvailabilityTable").find_all('tr')[1:]:
        cols = row.find_all('td')
        yield dict(cat_no=int(cols[2].text.strip()), session=int(cols[3].text.strip()), title=cols[4].text.strip(), enrolled=int(cols[7].text.strip()))


def run(year_start=None, num_years=10, minimum_cat_no=1000, save_to=None):
    """
    Collect all enrollment numbers of a given period.
    
    Parameters
    ----------
    year_start : None or int
        Year to start collecting (Default: current year)
    num_years : int
        Numbers of years to collect (Default: 10)
    minimum_cat_no : None or int
        Minimum catalog number (Default: 1000)
    save_to : None or str
        Save to file path if given (Default: not saved)

    Returns
    -------
    enrollment_table : astropy.table.Table
    """
    year_start = int(year_start or time.gmtime().tm_year)
    year_end = year_start - int(num_years)
    terms = sum([[("Spring", year+1), ("Fall", year)] for year in range(year_start, year_end, -1)], start=[])

    cols = ["cat_no", "session", "enrolled"]
    t_all = []
    for semester, year in terms:
        term_key = semester_year_to_term_key(semester, year)
        t = Table(rows=fetch_classes(term_key, "ASTR"))
        if not len(t):
            continue
        if minimum_cat_no:
            t = t[t["cat_no"] >= int(minimum_cat_no)]
        
        t = join(t, Table(rows=fetch_classes(term_key, "PHYS"))[cols], cols[:2], join_type="left", table_names=["astr", "phys"])
        t["enrolled_phys"].fill_value = 0
        t = t.filled()

        t["year"] = year
        t["semester"] = semester
        t_all.append(t)

    t_all = vstack(t_all)
    t_all["enrolled_all"] = t_all["enrolled_astr"] + t_all["enrolled_phys"]
    t_all = t_all[["year", "semester", "cat_no", "session", "title", "enrolled_astr", "enrolled_phys", "enrolled_all"]]
    if save_to:
        t_all.write(save_to, format="ascii.csv", overwrite=True)
    
    return t_all
    

def main():
    """
    Provides a command-line interface
    """
    parser = argparse.ArgumentParser(description="Script to fetch enrollment numbers for U Utah astro classes")
    parser.add_argument('-s', '--start-year', type=int, default=0, help='Year to start collecting (Default: current year)')
    parser.add_argument('-n', '--number-of-years', type=int, default=10, help='Numbers of years to collect (Default: 10)')
    parser.add_argument('-o', '--output-path', default='enrollment.csv', help='Output file path (Default: enrollment.csv)')
    parser.add_argument('-m', '--minimum-catalog-number', type=int, default=1000, help='Minimum catalog number (Default: 1000)')
    args = parser.parse_args()
    run(args.start_year, args.number_of_years, args.minimum_catalog_number, args.output_path)


if __name__ == "__main__":
    main()

