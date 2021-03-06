

import asyncio
from pprint import pprint
from time import sleep
from PyQt5 import QtCore, QtGui, QtWidgets,uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
import sys
import pandas as pd
import threading
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import re
import traceback
import numpy as np
import pywhatkit
import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(os.path.join('UI','ui.ui'), self)
        self.setWindowTitle('Tickets Checker')

        # connect the buttons
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        
        # desable stop button
        self.stop_btn.setEnabled(False)

        # define stop status 
        self.stop_status = False

        # initiate the filling data (loaded data from the excel file)
        self.data = []

        # state of data
        self.data_state = 'global'

        # initiate the table
        self.init_table()

        # the tickets that should be updated every amount of time
        self.checked_tickets_by_match_id = []
        self.updated_data = []




    def get_urls(self):
        df = pd.read_excel("data/matches.xlsx")
        return df['URL'].tolist()

    def get_data_for_table(self):
        data = []
        for row in self.data:
            row_t = []
            row_t.append(row['match'])
            row_t.append(f"{row['match']} - {row['host_vs_opposing']}")
            row_t.append(row['stadium'])
            for k in [1,2,3]:
                row_t.append(int(row[f'cat {k}']['is_available']))
            data.append(row_t)

        return sorted(data, key=lambda x:x[0])

    def fill_table(self):
        # get the urls
        urls = self.get_urls()

        # scrap the urls
        self.data_state = 'global'
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.get_page_info, urls)

        data = self.get_data_for_table()
        # fill the table
        self.table.setRowCount(len(data))
        for row_id, row in enumerate(data):
           for col_id in range(len(row)):
                if col_id in [3,4,5]:
                    item = QTableWidgetItem(str(row[col_id]))
                    item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    self.table.setItem(row_id, col_id, item)
                else :
                    self.table.setItem(row_id, col_id, QtWidgets.QTableWidgetItem(str(row[col_id])))

    
    def init_table(self):
        # set default checkbox
        self.dom_checkbox.setChecked(True)
        self.is_dom = True

        self.intl_checkbox.setChecked(False)
        self.is_intl = False

        self.fill_table()

    def get_page_content(self, url):
            # Get the page content
            header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
            }

            response = requests.get(url, headers=header)
            if response.status_code != 200:
                print("Error fetching page")
            else:
                content = response.content

            return BeautifulSoup(content, 'html.parser')

    def get_categories(self, all_cats):
        categories = []
        allowed_cats = [1,2,3]
        for cat in all_cats:
            category_name = cat.select(".category")
            if category_name:
                category_num = re.findall(r'\b\d+\b', category_name[0].text)
                if category_num:
                    category_num = int(category_num[0])
                    if category_num in allowed_cats:
                        categories.append(
                            {
                                "cat":cat,
                                "idx_name":f'cat {category_num}'
                            }
                        )
            else:
                continue
        return categories

    def get_page_info(self, url):
        try:
                        
            # Get the page content
            if self.is_dom and (not self.is_intl):
                _url = url.replace("intl","dom")
                soup = self.get_page_content(_url)

            else:
                soup = self.get_page_content(url)

            data = {'intl_url':'', 'dom_url':''}
            

            # get host_vs_opposing
            host = soup.select(".host")[0].text.strip()
            opposing = soup.select(".opposing")[0].text.strip()
            host_vs_opposing = f"{host} vs {opposing}"
            data['host_vs_opposing'] = host_vs_opposing

            # get stadium
            stadium = soup.select(".location")[-1].text.strip()
            data['stadium'] = stadium

            # get match number
            match = int(soup.select(".round")[0].text.lower().replace("match","").strip())
            data['match'] = match

            # initiate categories
            for k in [1,2,3]:
                data[f'cat {k}'] = {'is_dom_available':False, 'is_intl_available':False}

            if self.is_intl:
                data['intl_url'] = url
                # get the page categories (intl shope)
                all_intl_cats = soup.select('tbody tr')
                intl_cats     = self.get_categories(all_intl_cats)
                
                # check if the categories are available for intl 
                for inrl_cat in intl_cats:
                    intl_quantity = inrl_cat['cat'].select('.quantity ')
                    if intl_quantity:
                        data[inrl_cat['idx_name']]['is_intl_available'] = ("Currently unavailable" not in intl_quantity[0].text) 

            if self.is_dom:
                
                # get the page categories (dom shope)
                dom_url = url.replace("intl","dom")
                data['dom_url'] = dom_url
                dom_soup = self.get_page_content(dom_url)
                all_dom_cats = dom_soup.select('tbody tr')
                dom_cats    = self.get_categories(all_dom_cats)
            

                # check if the categories are available for dom
                for dom_cat in dom_cats:   
                    dom_quantity = dom_cat['cat'].select('.quantity ')
                    if dom_quantity:
                        data[dom_cat['idx_name']]['is_dom_available'] = ("Currently unavailable" not in dom_quantity[0].text)
            
            for k in [1,2,3]:
                if self.is_dom and not (self.is_intl):
                    data[f'cat {k}']['is_available'] = data[f'cat {k}']['is_dom_available']
                elif self.is_intl and not (self.is_dom):
                    data[f'cat {k}']['is_available'] = data[f'cat {k}']['is_intl_available']
                else:
                    data[f'cat {k}']['is_available'] = (data[f'cat {k}']['is_dom_available'] or data[f'cat {k}']['is_intl_available'])


            if self.data_state == 'global':
                self.data.append(data)
            else:
                self.updated_data.append(data)

        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print(traceback.format_exc())

    def get_checked_tickets_by_match_id(self):
        checked_tickets = []
        for row_id in range(self.table.rowCount()):
            checked_row = {
                'match_id':None,
                'ticket_categories':[]
            }
            for col_id in range(3,6):
                if self.table.item(row_id, col_id).checkState() == Qt.CheckState.Checked:
                    checked_row['match_id'] = self.table.item(row_id, 0).text()
                    checked_row['ticket_categories'].append(self.table.horizontalHeaderItem(col_id).text())
            if checked_row['match_id'] != None:
                checked_tickets.append(checked_row)
        checked_tickets = sorted(checked_tickets, key=lambda x: int(x['match_id']))
        return checked_tickets

    def get_urls_by_match_id(self):
        urls = []
        df = pd.read_excel("data/matches.xlsx")
        for ticket in self.checked_tickets_by_match_id :
            url_idx = np.where(df['Match'].apply(lambda x: int(x.replace("#",""))) == int(ticket['match_id']))[0][0]
            url = df['URL'][url_idx]
            urls.append(url)
        return urls

    def send_telegram_msg(self,phone_number, msg):
        load_dotenv()

        api_id = os.getenv("api_id")
        api_hash = os.getenv("api_hash")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = TelegramClient(StringSession(os.getenv("session_token")), api_id, api_hash, loop=loop)
            client.start()
        except Exception as e:
            print(f"Exception while starting the client - {e}")
        else:
            print("Client started")

        async def send():
            try:
                # Replace the xxxxx in the following line with the full international mobile number of the contact
                # In place of mobile number you can use the telegram user id of the contact if you know
                ret_value = await client.send_message(phone_number, msg)
            except Exception as e:
                print(f"Exception while sending the message - {e}")
            else:
                print(f"Message sent.")

        with client:
            client.loop.run_until_complete(send())

    def send_msg(self, match_id, category_idx, ticket_url):
        msg = f'''
        good news!\nticket available for match {match_id}\ncategory: {category_idx}\nticket url: {ticket_url}
        '''
        # send mesg to whatsapp
        if self.wts_checkbox.isChecked():
            # get the phone number from QlineEdit
            phone_number = self.phone_input.text()
            self.send_telegram_msg(phone_number, msg)
        # send mesg to email

    def notify_user(self, match_id, category_idx, is_dom_available, is_intl_available, urls):
        if is_dom_available and is_intl_available:
            self.send_msg(match_id, category_idx, '\n'.join(urls))
        elif is_dom_available:
            self.send_msg(match_id, category_idx, urls[0])
        elif is_intl_available:
            self.send_msg(match_id, category_idx, urls[1])


    def update_table_category_by_match_id(self,match_id, category_idx, is_dom_available, is_intl_available, urls):
        try:
            for row_id in range(self.table.rowCount()):
                if int(self.table.item(row_id, 0).text()) == int(match_id):
                    if (int(self.table.item(row_id ,category_idx).text()) == 0) :
                        # update category
                        item = QTableWidgetItem(str(1))
                        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                        item.setCheckState(Qt.CheckState.Checked)
                        self.table.setItem(row_id, category_idx, item)
                        
                        print(f"-------> Match {match_id} category {category_idx-2} is available")
                        self.notify_user(match_id, category_idx-2, is_dom_available, is_intl_available, urls)
        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print(traceback.format_exc())

    def update_categories_availability(self):

        print("Updating categories availability thread started")
        
        urls = self.get_urls_by_match_id()

        while not self.stop_status:
            print("Inside the thread...")
            self.updated_data = []

            # scrap the urls
            self.data_state = 'not global'
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self.get_page_info, urls)

            self.updated_data = sorted(self.updated_data, key=lambda x: int(x['match']))


            # update the categories in the table
            for idx, ticket in enumerate(self.updated_data):
                for category in self.checked_tickets_by_match_id[idx]['ticket_categories']:
                    category = category.lower()

                    #### test
                    ticket[category]['is_available'] = True
                    ticket[category]['is_dom_available'] = True
                    ticket[category]['is_intl_available'] = True
                    ####

                    if ticket[category]['is_available'] :
                        category_index = int(category.lower().replace("cat","").strip())+2
                        self.update_table_category_by_match_id(ticket['match'], category_idx = category_index , 
                        is_dom_available = ticket[category]['is_dom_available'], is_intl_available = ticket[category]['is_intl_available'], urls=[ticket['dom_url'], ticket['intl_url']])
            sleep(5)

        self.start_btn.setEnabled(True)
        self.stop_status = False

        print("Update categories availability thread stopped")

    def start(self):
        print("Starting...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # initiate shops
        self.is_dom = self.dom_checkbox.isChecked()
        self.is_intl = self.intl_checkbox.isChecked()
        
        # get the checked tickets
        self.checked_tickets_by_match_id = self.get_checked_tickets_by_match_id()

        # update the table with the checked tickets
        update_cats_thread = threading.Thread(target=self.update_categories_availability)
        update_cats_thread.start()

    def stop(self):
        self.stop_btn.setEnabled(False)
        self.stop_status = True
        



if __name__ == "__main__":
    App = QtWidgets.QApplication(sys.argv)  
    OutputDialog = QtWidgets.QStackedWidget()
    #UIs
    ui = Ui()
    # set size of win
    OutputDialog.setFixedSize(1073, 749)
    #add wins
    OutputDialog.addWidget(ui)
    # disable X button
    #OutputDialog.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
    OutputDialog.show()
    sys.exit(App.exec_())
        
        

