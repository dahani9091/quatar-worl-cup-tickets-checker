

from pprint import pprint
from time import sleep
from PyQt5 import QtCore, QtGui, QtWidgets,uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
import os
import sys
import pandas as pd
import threading
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import re
import traceback
import numpy as np

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
                row_t.append(int(row[f'cat {k}']['is_intl_available'] or row[f'cat {k}']['is_dom_available']))
            for k in [1,2,3]:
                shope = ""
                if row[f'cat {k}']['is_intl_available']:
                    shope += "Intl "
                if row[f'cat {k}']['is_dom_available']:
                    shope += "Dom "
                row_t.append(shope.strip())
            data.append(row_t)


        return sorted(data, key=lambda x:x[0])

    def fill_table(self):
        # get the urls
        urls = self.get_urls()

        # scrap the urls
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
        self.fill_table()
        self.data_state = 'updated data'

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
            soup = self.get_page_content(url)

            data = {}

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

            # get the page categories (intl shope)
            all_intl_cats = soup.select('tbody tr')
            intl_cats     = self.get_categories(all_intl_cats)

            # get the page categories (dom shope)
            dom_url = url.replace("intl","dom")
            dom_soup = self.get_page_content(dom_url)
            all_dom_cats = dom_soup.select('tbody tr')
            dom_cats    = self.get_categories(all_dom_cats)

            # initiate categories
            for k in [1,2,3]:
                data[f'cat {k}'] = {'is_dom_available':False, 'is_intl_available':False}

            # check if the categories are available for intl 
            for inrl_cat in intl_cats:
                intl_quantity = inrl_cat['cat'].select('.quantity ')
                if intl_quantity:
                    data[inrl_cat['idx_name']]['is_intl_available'] = ("Currently unavailable" not in intl_quantity[0].text)            

            # check if the categories are available for dom
            for dom_cat in dom_cats:   
                dom_quantity = dom_cat['cat'].select('.quantity ')
                if dom_quantity:
                    data[dom_cat['idx_name']]['is_dom_available'] = ("Currently unavailable" not in dom_quantity[0].text)
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
        
    def update_table_category_by_match_id(self,match_id, category_idx,is_available, is_dom_available, is_intl_available):
        try:
            for row_id in range(self.table.rowCount()):
                if int(self.table.item(row_id, 0).text()) == int(match_id):
                    if (int(self.table.item(row_id ,category_idx).text()) == 0) :
                        # update category
                        item = QTableWidgetItem(str(1))
                        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                        item.setCheckState(Qt.CheckState.Checked)
                        self.table.setItem(row_id, category_idx, item)

                        # update shop
                        shop  = ""
                        if is_intl_available:
                            shop += "intl "
                        if is_dom_available:
                            shop += "dom"
                        self.table.setItem(row_id, category_idx+3, QtWidgets.QTableWidgetItem(shop.strip()))
                        
                        print(f"-------> Match {match_id} category {category_idx} is available")
                        # notify the user that the ticket is available
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
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self.get_page_info, urls)

            self.updated_data = sorted(self.updated_data, key=lambda x: int(x['match']))


            # update the categories in the table
            for idx, ticket in enumerate(self.updated_data):
                for category in self.checked_tickets_by_match_id[idx]['ticket_categories']:
                    category = category.lower()
                    if (ticket[category]['is_dom_available'] or ticket[category]['is_intl_available']):
                        category_index = int(category.lower().replace("cat","").strip())+2
                        self.update_table_category_by_match_id(ticket['match'], category_idx = category_index, is_available = 1, 
                        is_dom_available = ticket[category]['is_dom_available'], is_intl_available = ticket[category]['is_intl_available'])
            sleep(5)

        self.start_btn.setEnabled(True)
        self.stop_status = False

        print("Update categories availability thread stopped")

    def start(self):
        print("Starting...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        
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
        
        

