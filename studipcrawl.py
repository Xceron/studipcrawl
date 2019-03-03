# coding: utf8
import platform
import shutil
import requests
import re
import zipfile
import io
import pickle
import os
from bs4 import BeautifulSoup

### ----------------------------SETUP---------------------------- ###
# Only change this part of the program
# Change this to your username used in Studip
USERNAME = "USERNAME"
# Change this to your password used in Studip
PASSWORD = "PASSWORD"
# Change this to the destination path where the files should be
# downloaded. The r"" has to stay in order to work!
DST_FOLDER = r"PATH/TO/DIR"
### ------------------------------------------------------------- ###

def get_files():
    """
    :return: downloads all files/folders from Studip
    """
    sl = slash()
    with requests.Session() as r:
        homepage = r.get(URL_LOGIN)
        soup = BeautifulSoup(homepage.text, "html.parser")
        security_token = soup.find("input", {"name": "security_token"})["value"]
        login_ticket = soup.find("input", {"name": "login_ticket"})["value"]
        try:
            payload = {"security_ticket": security_token,
                       "login_ticket": login_ticket,
                       "loginname": USERNAME,
                       "password": PASSWORD}
            login_start = r.post(URL_LOGIN, data=payload)
            if "angemeldet" in login_start.text:
                print("Login successful!")
            else:
                print("Wrong password and/or username")
                exit()
        except AttributeError:
            # weird cases where AttributeError gets thrown
            get_files()
        my_courses = r.get("https://studip.uni-trier.de/dispatch.php/my_courses")
        my_courses_links = get_links_from_site(my_courses.text, "2Fcourse%2Ffiles")
        module_links = []
        for j in range(len(my_courses_links)):  # gathers all links to My Courses
            if my_courses_links[j] == my_courses_links[j - 1]:
                course_id = re.search("auswahl=(.*)&", my_courses_links[j]).group(1)
                course_id = course_id.replace("auswahl=", "")
                course_id = course_id.replace("&amp", "")
                module_links.append("https://studip.uni-trier.de/dispatch.php/course/files?cid=" + course_id)
        for sites in module_links:  # My Courses - files overview site
            site_get = r.get(sites)
            save_cookies(r.cookies, "cookies")
            soup = BeautifulSoup(site_get.text,"html.parser")
            folder_name = make_folder_name(soup.find("title")["data-original"])
            if not os.path.exists(DST_FOLDER + sl + folder_name):  # checks if the folder already exists
                os.makedirs(DST_FOLDER + sl + folder_name)  # creates destination folder
            download_folder(site_get, DST_FOLDER + sl + folder_name)


def make_folder_name(old_name):
    """
    :param old_name: unformatted name
    :return: gets rid of useless words for a easier to find folder name in dst_folder
    """
    for sign in ["Vorlesung", "Übung", "Tutorium", " - Dateien", ": "]:
        old_name = old_name.replace(sign, "")
    return old_name


def save_cookies(requests_cookiejar, filename):
    """
    :param requests_cookiejar: CookieJar object
    :param filename: filename of the cookie
    :return: saves the cookie in the same directory as this .py
    """
    with open(filename, "wb") as f:
        pickle.dump(requests_cookiejar, f)


def load_cookies(filename):
    """
    :param filename: filename used in save_cookies
    :return: cookieJar object used for saving the session
    """
    with open(filename, "rb") as f:
        return pickle.load(f)

def get_links_from_site(html, url):
    """
    :param html: html text
    :param url: url with regex
    :return: list with urls
    """
    soup = BeautifulSoup(html, "html.parser")
    site_tags = soup.find_all("a", href=re.compile(url))
    links = [tags.get("href") for tags in site_tags]
    return links

def download_folder(url, path):
    """
    :param url: url to a a site containing files and/or folders
    :param path: path to dir to download
    :return: download file to the directory and rename it accordingly
    """
    sl = slash()
    cookies = load_cookies("cookies")
    folder_url = get_links_from_site(url.text, "https://studip.uni-trier.de/dispatch.php/file/download_folder/+(.*)")
    for folders in folder_url:
        response = requests.get(folders, stream=True, cookies=cookies)
        z = zipfile.ZipFile(io.BytesIO(response.content))
        z.extractall(path)
        with open(path + sl + "PLACEHOLDER_TO_DELETE", "wb") as out_file:
            out_file.write(response.content)
        print("Successfully downloaded a folder!")
    files_url = get_links_from_site(url.text, "https://studip.uni-trier.de/dispatch.php/file/details/+(.*)")
    for files in files_url:
        overview_page = requests.get("https://studip.uni-trier.de/dispatch.php/file/details/" + files, stream=True,
                                     cookies=cookies)
        if "Herunterladen" in overview_page.text:
            file_url = get_links_from_site(overview_page.text, "https://studip.uni-trier.de/sendfile.php(.*)")[0]
            try:
                fixed_url = file_url.group(1).replace("&amp;", "&")
                response = requests.get("https://studip.uni-trier.de/sendfile.php" + fixed_url, cookies=cookies)
                file_name = re.search("file_name=(.*)", fixed_url)
                file_name = file_name.group(1)
                file_name = file_name.replace("+", " ")
                with open(path + sl + file_name, "wb") as out_file:
                    out_file.write(response.content)
                print("Successfully downloaded a file!")
            except AttributeError:
                download_folder(url, path)
        else:
            pass


def slash():
    """
    :return: appropiate slash for Unix/macOS or Windows based systems
    """
    if platform.system() == "Windows":
        return "\\"
    else:
        return "//"


def cleanup(path):
    """
    :return: deletes duplicates and removes useless files
    """
    sl = slash()
    for folder in os.listdir(path):
        if folder == ".DS_Store":
            os.remove(path + sl + folder)
        else:
            for subfolder in os.listdir(path + sl + folder):
                path_sb = path + sl + folder + sl
                if subfolder == ".DS_Store":
                    os.remove(path_sb + ".DS_STORE")
                if subfolder == "PLACEHOLDER_TO_DELETE":
                    os.remove(path_sb + "PLACEHOLDER_TO_DELETE")
                if subfolder == "archive_filelist.csv":
                    os.remove(path_sb + "archive_filelist.csv")
                if subfolder == "Allgemeiner Dateiordner":
                    for files in os.listdir(path_sb + sl + "Allgemeiner Dateiordner"):
                        path_ad = path_sb + "Allgemeiner Dateiordner" + sl + files
                        if os.path.isdir(path_ad):
                            check_folder(path_ad, path_sb + files)
                        elif os.path.isfile(path_ad):
                            check_duplicates(path_ad, path_sb + files)
                        else:
                            pass
                    shutil.rmtree(path_sb + "Allgemeiner Dateiordner")
    os.remove("cookies")


def check_duplicates(src_path, dst_path):
    """
    :param src_path: path to file to check in temporary folder
    :param dst_path:  path to file to check in final folder
    :return: deletes smaller file and moves the bigger one to the final folder
    """
    if os.path.exists(dst_path):  # duplicate files
        if os.path.isfile(dst_path):  # handling files
            if os.path.getsize(src_path) > os.path.getsize(dst_path):
                print("Found newer version of file, moving: " + os.path.basename(dst_path))
                os.remove(dst_path)
                os.rename(src_path, dst_path)
            else:  # existing file >= file in downloaded dir
                print("Deleting downloaded file: " + os.path.basename(src_path))
                os.remove(src_path)
    else:  # downloaded file is new
        print("Moving new file: " + os.path.basename(dst_path))
        os.rename(src_path, dst_path)


def check_folder(src_path, dst_path):
    """
    :param src_path: path to folder to check in temporary folder
    :param dst_path:  path to folder to check in final folder
    :return: recursively checks folders and calls check_duplicate()
    """
    sl = slash()
    if os.path.exists(dst_path):
        if os.path.isdir(dst_path):
            for subcontent in os.listdir(src_path):
                if os.path.isdir(dst_path + sl + subcontent):
                    check_folder(src_path + sl + subcontent, dst_path + sl + subcontent)
                else:
                    check_duplicates(src_path + sl + subcontent, dst_path + sl + subcontent)
    else:
        os.makedirs(dst_path)
        check_folder(src_path,dst_path)


if __name__ == "__main__":
    URL_LOGIN = "https://studip.uni-trier.de/index.php?again=yes"
    get_files()
    cleanup(DST_FOLDER)
    exit()
