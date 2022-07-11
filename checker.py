

import asyncio
from concurrent.futures import thread
# qt imports
from PyQt5 import  QtGui, QtWidgets,uic, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import  QTableWidgetItem, QApplication
# local imports
import sys
from time import sleep
import os
import re
import threading
import requests
# data collection imports 
import pandas as pd
from bs4 import BeautifulSoup
import concurrent.futures
import traceback
import numpy as np
import pickle
# sending notification imports
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
import smtplib
# play sounds
import simpleaudio as sa




#dir_path = os.path.dirname(os.path.realpath(__file__))

session_token='1BJWap1wBu6SGPv0C8xdncdil9Lwa8c9m5QaO_Q56boVJRPfNQ-6YZIDUdWBZSH0ovpRviyJ8fTuIWzycIE337p2hnHDRFZaCnXfDlaXerBAV58QlbiBE58nxDU0zctVfUp-6UqtZ7dtXEjfqutbcB3QuizuMpLSWx42358oWkfqWI0U2RGUcWxKnOs5dumy3k9mwEkF6YoFUxJkMN3_009A-FhLVY9w9F_AeGZN4Sq8j0G6FIgNP85ZwndakNBgeyzW5qYykcreYzStUdFPCIi61lAKISS4rktw5Wd7AwBLHkDBHygiVHDrH2apv_R6YvOZZw6w88w4piHa0bJD57sM6eGYchew='
api_id='10320937'
api_hash='44aeeae18fe82d65fe4829e21db6326d' 
gmail_user='Qatar2022TicketScanner@gmail.com'
gmail_password='ykujtaszobuwpjju'


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(os.path.join(os.getcwd(),"UI/ui.ui"), self)
        self.setWindowTitle('Tickets Checker')


        # connect the buttons
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.update_btn.clicked.connect(self.force_update_table)

        # desable stop button
        self.stop_btn.setEnabled(False)

        # define stop status 
        self.stop_status = False

        # initiate the filling data (loaded data from the excel file)
        self.data = []

        # state of data
        self.data_state = 'global'

        # set default checkbox
        self.dom_checkbox.setChecked(True)
        self.is_dom = True

        self.intl_checkbox.setChecked(False)
        self.is_intl = False


        # initiate the table
        self.table.setStyleSheet('QAbstractItemView::indicator {width:20; height:20;} QTableWidget::item {margin-left:50%; margin-right:50%;}')
        self.setStyleSheet('''

                        QProgressBar {
                            background-color: #DA7B93;
                            color: rgb(200, 200, 200);
                            border-style: none;
                            border-radius: 10px;
                            text-align: center;
                            font-size: 30px;
                        }

                        QProgressBar::chunk {
                            border-radius: 10px;
                            background-color: qlineargradient(spread:pad x1:0, x2:1, y1:0.511364, y2:0.523, stop:0 #1C3334, stop:1 #376E6F);
                        }
                    ''')
        # resize the first column of the table
        self.table.setColumnWidth(1, 270)
        self.table.setColumnWidth(2, 220)
        self.init_table()

        # the tickets that should be updated every amount of time
        self.checked_tickets_by_match_id = []
        self.updated_data = []




    def get_urls(self):
        with open(os.path.join(os.getcwd(),"db/db.pkl"), "rb") as f:
            df = pickle.load(f)
        return df['URL'].tolist()

    def get_data_for_table(self):
        data = []
        for row in self.data:
            row_t = []
            row_t.append(row['match'])
            row_t.append(f"{row['host_vs_opposing']}")
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
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(Qt.CheckState.Unchecked)

                    self.table.setItem(row_id, col_id, item)
                    if int(row[col_id]) == 1:
                        self.table.item(row_id, col_id).setBackground(QtGui.QColor(0, 255, 0))
                    else:
                        self.table.item(row_id, col_id).setBackground(QtGui.QColor(255, 0, 0))
                else :
                    self.table.setItem(row_id, col_id, QtWidgets.QTableWidgetItem(str(row[col_id])))

    
    def init_table(self):
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
        with open(os.path.join(os.getcwd(),"./db/db.pkl"), "rb") as f:
            df = pickle.load(f)
        for ticket in self.checked_tickets_by_match_id :
            url_idx = np.where(df['Match'].apply(lambda x: int(x.replace("#",""))) == int(ticket['match_id']))[0][0]
            url = df['URL'][url_idx]
            urls.append(url)
        return urls

    def send_telegram_msg(self,tg_username, msg):
        load_dotenv()


        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = TelegramClient(StringSession(session_token), api_id, api_hash, loop=loop)
            client.start()
        except Exception as e:
            print(f"Exception while starting the client - {e}")
        else:
            print("Client started")

        async def send():
            try:
                # Replace the xxxxx in the following line with the full international mobile number of the contact
                # In place of mobile number you can use the telegram user id of the contact if you know
                ret_value = await client.send_message(tg_username, msg)
            except Exception as e:
                print(f"Exception while sending the message - {e}")
            else:
                print(f"Message sent.")

        with client:
            client.loop.run_until_complete(send())

    def send_email(self, email, msg):
        try:
            SUBJECT = "Quatar World Cup Ticket availability"
            message = 'Subject: {}\n\n{}'.format(SUBJECT, msg)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, email, message)
            server.quit()
        except Exception as e:
            print(f"Exception while sending the email - {e}")
        else:
            print(f"Email sent.")

    def send_msg(self, match_id, category_idx, match_des ,ticket_url):
        msg = f'''
        good news!\n\nTicket Available for Match {match_id}:\n\n{match_des}\nCategory: {category_idx}\n\nTicket url: {ticket_url}
        '''
        # send mesg to telegram
        if self.telegram_checkbox.isChecked():
            # get the phone number from QlineEdit
            phone_number = self.tg_username_input.text()
            self.send_telegram_msg(phone_number, msg)
        # send mesg to email
        if self.email_checkbox.isChecked():
            # get the email from QlineEdit
            email = self.email_input.text()
            self.send_email(email, msg)

    def notify_user(self, match_id, category_idx, match_des ,is_dom_available, is_intl_available, urls):
        if is_dom_available and is_intl_available:

            self.send_msg(match_id, category_idx, match_des,'\n'.join(urls))
        elif is_dom_available:
            print("I'm here")
            self.send_msg(match_id, category_idx, match_des,urls[0])
        elif is_intl_available:
            self.send_msg(match_id, category_idx, match_des,urls[1])

    def play_voice_atert(self):
        # open the pickle file and load the wave object
        with open('db/icq.pkl', 'rb') as f:
            wave_object = pickle.load(f)
        # play it using simpleaudio
        print("Playing the voice alert...")
        play_object = wave_object.play()    
        play_object.wait_done()

    def update_table_category_by_match_id(self,match_id, category_idx, match_des ,is_dom_available, is_intl_available, urls):
        try:
            for row_id in range(self.table.rowCount()):
                if int(self.table.item(row_id, 0).text()) == int(match_id):
                    #if (int(self.table.item(row_id ,category_idx).text()) == 0) :
                    # update category
                    # set cell color to green
                    self.table.item(row_id, category_idx).setBackground(QtGui.QColor(0, 255, 0))
                    
                    print(f"-------> Match {match_id} category {category_idx-2} is available")
                    self.notify_user(match_id, category_idx-2, match_des, is_dom_available, is_intl_available, urls)
                    self.play_voice_atert()
        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print(traceback.format_exc())




    def update_all_table_categories(self, _from=None):
        self.is_intl = self.intl_checkbox.isChecked()
        self.is_dom  = self.dom_checkbox.isChecked()
        # get the urls
        urls = self.get_urls()

        # scrap the urls
        self.data = []
        self.data_state = 'global'
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.get_page_info, urls)
        data = self.get_data_for_table()

        # update table categories
        for row_id in range(self.table.rowCount()):
            for col_id in [3,4,5]:
                if int(data[row_id][col_id]) == 1:
                    self.table.item(row_id, col_id).setBackground(QtGui.QColor(0, 255, 0))
                else:
                    self.table.item(row_id, col_id).setBackground(QtGui.QColor(255, 0, 0))
        # scroll to the last item in the table
        self.table.scrollToBottom()
        # scroll to the first item in the table
        self.table.scrollToTop()

        if _from == "force_update":
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.update_btn.setEnabled(True)

    def update_categories_availability(self):

        print("Updating categories availability thread started")
        
        urls = self.get_urls_by_match_id()
        print("urls: ", len(urls))
        if self.waiting_time_input.text() != '':
            self.waiting_time = float(self.waiting_time_input.text())
        else:
            self.waiting_time = 5

        print(self.waiting_time)

        while not self.stop_status:
            print("Inside the thread...")
            self.updated_data = []

            # scrap the urls
            self.data_state = 'not global'
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self.get_page_info, urls)

            self.updated_data = sorted(self.updated_data, key=lambda x: int(x['match']))
            ##

            # update the categories in the table
            for idx, ticket in enumerate(self.updated_data):
                for category in self.checked_tickets_by_match_id[idx]['ticket_categories']:
                    category = category.lower()
                    if ticket[category]['is_available'] :
                        category_index = int(category.lower().replace("cat","").strip())+2
                        self.update_table_category_by_match_id(ticket['match'], category_idx = category_index , match_des = ticket['host_vs_opposing'] , 
                        is_dom_available = ticket[category]['is_dom_available'], is_intl_available = ticket[category]['is_intl_available'], urls=[ticket['dom_url'], ticket['intl_url']])
            self.update_all_table_categories()
            if self.stop_status:
                break
            sleep(self.waiting_time)
        self.change_checkboxes_state("enable")
        self.update_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_status = False

        print("Update categories availability thread stopped")

    def force_update_table(self):
        self.update_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        # show the waiting label
        # start loading thread
        # remove color from all the cells
        for row_id in range(self.table.rowCount()):
            for col_id in [3,4,5]:
                self.table.item(row_id, col_id).setBackground(QtGui.QColor(255, 255, 255))
        update_thre = threading.Thread(target=self.update_all_table_categories  ,args = ("force_update",))
        update_thre.start()
        while True:
            # make dom_checkbox checkbox checked
            self.dom_checkbox.setChecked(not self.is_dom)
            self.dom_checkbox.setChecked(self.is_dom)
            if not update_thre.is_alive():
                break
            





    def start(self):
        # desable checkboxes
        self.change_checkboxes_state("desable")

        # get selected shops
        self.is_intl = self.intl_checkbox.isChecked()
        self.is_dom  = self.dom_checkbox.isChecked()
        
        print("Starting...")
        self.start_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        
        # get the checked tickets
        self.checked_tickets_by_match_id = self.get_checked_tickets_by_match_id()

        # update the table with the checked tickets
        update_cats_thread = threading.Thread(target=self.update_categories_availability)
        update_cats_thread.start()
    def change_checkboxes_state(self, state):
        if state == "enable":
            for row_id in range(self.table.rowCount()):
                for col_id in [3,4,5]:
                    # enable the checkbox inside the cell
                    self.table.item(row_id, col_id).setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        else:
            for row_id in range(self.table.rowCount()):
                for col_id in [3,4,5]:
                    # enable the checkbox inside the cell
                    self.table.item(row_id, col_id).setFlags(Qt.ItemFlag.ItemIsEnabled)


    def stop(self):
        # enable checkboxes
        self.stop_btn.setEnabled(False)
        self.stop_status = True
        
        
#


if __name__ == "__main__":
    App = QtWidgets.QApplication(sys.argv)  
    OutputDialog = QtWidgets.QStackedWidget()
    # windows title
    OutputDialog.setWindowTitle("Qatar 2022 Ticket Scanner")
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
        
        

