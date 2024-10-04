#! /usr/bin/python3

# Push a CSV into an Explorance Blue data source
# https://jira.cilt.uct.ac.za/browse/AMA-1092

import requests
import os
import sys
import re
import json
import progressbar
import csv
import logging
import zeep
from html import escape

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config
from lib.local_auth import getAuth

class PushDataSource:
    def __init__(self,BlueWSURL,BlueAPIKey) -> None:
        self.BlueWSURL = BlueWSURL
        self.EndPoint = self.BlueWSURL+"/BlueWebService.svc/file"
        self.wsdl = self.BlueWSURL+"/BlueWebService.svc?wsdl"
        self.BlueAPIKey = BlueAPIKey
        self.TransactionId = ''
        self.DataSourceID = ''
        self.client = zeep.Client(wsdl=self.wsdl)

    def GetDataSourceID(self):
        return 0

    def getDataSourceList(self):
        response = self.client.service.GetDataSourceList(_soapheaders={'APIKeyHeader': self.BlueAPIKey})
        ds = response['body']['DataSources']['IDataSource']
        return ds

    # GetDataBlockInformation()
    def getDataBlockInformation(self, datasource_id):
        response = self.client.service.GetDataBlockInformation(_soapheaders={'APIKeyHeader': self.BlueAPIKey, 'DatasourceId' : datasource_id})
        dbi = response['body']['DataBlockInfoList']['DataBlockInfo']
        return dbi

    def RegisterImport(self,DataSourceID,AbortOnEmpty='true',ReplaceBlueRole='false',ReplaceDataSourceAccessKey='false',ReplaceLanguagePreferences='false'):
        self.DataSourceID = DataSourceID
        payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                        <soapenv:Header>
                            <tem:APIKeyHeader>"""+self.BlueAPIKey+"""</tem:APIKeyHeader>
                        </soapenv:Header>
                        <soapenv:Body>
                            <tem:RegisterImportRequest>
                                <tem:AbortOnEmpty>"""+AbortOnEmpty+"""</tem:AbortOnEmpty>
                                <tem:DataSourceID>"""+DataSourceID+"""</tem:DataSourceID>
                                <tem:ReplaceBlueRole>"""+ReplaceBlueRole+"""</tem:ReplaceBlueRole>
                                <tem:ReplaceDataSourceAccessKey>"""+ReplaceDataSourceAccessKey+"""</tem:ReplaceDataSourceAccessKey>
                                <tem:ReplaceLanguagePreferences>"""+ReplaceLanguagePreferences+"""</tem:ReplaceLanguagePreferences>

                            </tem:RegisterImportRequest>
                        </soapenv:Body>
                    </soapenv:Envelope>"""
        headers = {'Content-Type': 'text/xml;charset=UTF-8',
                   'SOAPAction': '"http://tempuri.org/IBlueWebService/RegisterImport"'}
        response = requests.request("POST", self.EndPoint, headers=headers, data = payload)
        print(f"RegisterImport : {response}")
        print(f"RegisterImport : {payload}")
        if response.status_code==200:
            m = re.search('<TransactionID>(.+?)</TransactionID>', response.text)
            # print(m)
            if m:
                self.TransactionId = m.group(1)
                print(f"self.TransactionId : {self.TransactionId}")
                return True
        return False

    def PushObjectDataV2(self, DataSourceID, csv_file):
        # print(f"THIS IS TRANS AC ID: {self.TransactionId}")
        # with open("C:/Users/laithdodin/Python_Projects/BlueWebServices/UCT Sandbox/Data.json") as file:
        with open(csv_file) as file:
        # with open("data.json") as file:
            reader = csv.DictReader(file)
            Header = "<tem:ColumnNamesList>"
            for fieldname in reader.fieldnames:
                Header += f"<arr:string>{fieldname}</arr:string>"
            Header += "</tem:ColumnNamesList>"

            # print(Header)
            xml_data  = "<tem:Data>"
            for row in reader:
                xml_data  += "<blue:IDataRow><blue:IDataRowValue>"

                for k, v in row.items():
                    xml_data  += f"<blue:IDataObj><blue:IDataObjValue>{v}</blue:IDataObjValue></blue:IDataObj>"
                xml_data  += "</blue:IDataRowValue></blue:IDataRow>"
            xml_data  += "</tem:Data>"

            TransactionId = self.TransactionId
            # TransactionId = '6821714594214839372'
            DataSourceID = str(DataSourceID)
            Header = str(Header)  # Header should already be a string, but convert it just in case
            row = row

            print(f"TransactionId : {TransactionId} - DataSourceID : {DataSourceID} - Header : {Header} - row : {row}")
            # payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/" xmlns:arr="http://schemas.microsoft.com/2003/10/Serialization/Arrays" xmlns:blue="http://schemas.datacontract.org/2004/07/Blue.Integration">
            payload = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                            xmlns:tem="http://tempuri.org/"
                            xmlns:arr="http://schemas.microsoft.com/2003/10/Serialization/Arrays"
                            xmlns:blue="http://schemas.datacontract.org/2004/07/Blue.Integration">
                            <soapenv:Header>
                                <tem:TransactionId>{TransactionId}</tem:TransactionId>
                                <tem:DataBlockName>{DataSourceID}</tem:DataBlockName>
                                {Header}
                                <tem:APIKeyHeader>{self.BlueAPIKey}</tem:APIKeyHeader>
                            </soapenv:Header>
                            <soapenv:Body>
                                <tem:DataObjectTransferRequestV2>
                                {xml_data}
                                </tem:DataObjectTransferRequestV2>
                            </soapenv:Body>
                            </soapenv:Envelope>"""

            headers = {
                'Content-Type': 'text/xml;charset=UTF-8',
                'SOAPAction': '"http://tempuri.org/IBlueWebService/PushObjectDataV2"'
                }

            response = requests.request("POST", self.EndPoint, headers=headers, data = payload)

            if response.status_code==200:
                return True
            else:
                print(response.content)
                self.CancelImport()
                return False

    def PrepareDataToFinzalizeImportV2(self):
        payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                        <soapenv:Header>
                            <tem:TransactionID>"""+self.TransactionId+"""</tem:TransactionID>
                            <tem:APIKeyHeader>"""+self.BlueAPIKey+"""</tem:APIKeyHeader>
                        </soapenv:Header>
                        <soapenv:Body>
                            <tem:BasicRequest/>
                        </soapenv:Body>
                        </soapenv:Envelope>"""
        headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': '"http://tempuri.org/IBlueWebService/PrepareDataToFinzalizeImportV2"'
        }
        response = requests.request("POST", self.EndPoint, headers=headers, data = payload)
        print(f"PrepareDataToFinzalizeImportV2 : {response}")
        if response.status_code==200:
            return True
        else:
            print(response.content)
            self.CancelImport()
            return False

    def FinalizeImport(self):
        payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                    <soapenv:Header>
                        <tem:TransactionID>"""+self.TransactionId+"""</tem:TransactionID>
                        <tem:APIKeyHeader>"""+self.BlueAPIKey+"""</tem:APIKeyHeader>
                    </soapenv:Header>
                    <soapenv:Body>
                        <tem:FinalizeImportRequest/>
                    </soapenv:Body>
                    </soapenv:Envelope>"""
        headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': '"http://tempuri.org/IBlueWebService/FinalizeImport"'
        }
        response = requests.request("POST", self.EndPoint, headers=headers, data = payload)
        if response.status_code==200:
            return True
        else:
            self.CancelImport()
            return False


    def CancelImport(self):
        payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                        <soapenv:Header>
                            <tem:TransactionID>"""+self.TransactionId+"""</tem:TransactionID>
                            <tem:APIKeyHeader>"""+self.BlueAPIKey+"""</tem:APIKeyHeader>
                        </soapenv:Header>
                        <soapenv:Body>
                            <tem:CancelImportRequest/>
                        </soapenv:Body>
                    </soapenv:Envelope>"""
        headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': '"http://tempuri.org/IBlueWebService/CancelImport"'
        }
        response = requests.request("POST", self.EndPoint, headers=headers, data = payload)
        return 0

    def GetProgressStatus(self):
        payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                        <soapenv:Header>
                            <tem:APIKeyHeader>"""+self.BlueAPIKey+"""</tem:APIKeyHeader>
                        </soapenv:Header>
                        <soapenv:Body>
                            <tem:ProgressStatusRequest>
                                <tem:DataSourceId>"""+self.DataSourceID+"""</tem:DataSourceId>
                            </tem:ProgressStatusRequest>
                        </soapenv:Body>
                    </soapenv:Envelope>"""
        headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': '"http://tempuri.org/IBlueWebService/GetProgressStatus"'
        }
        response = requests.request("POST", self.EndPoint, headers=headers, data = payload)
        if response.status_code==200:
            m = re.search('<ProgressStatus>(.+?)</ProgressStatus>', response.text)
            if m:
                return int(m.group(1))
        return False

#######

def main():

    blue_api = getAuth('BlueTest', ['apikey', 'url'])

    if not blue_api['valid']:
        raise Exception("Missing configuration")

    logging.info(f"Explorance endpoint {blue_api['url']}")

    csv_file = "courses-small.csv"
    datasource_id = "Data25"
    datablock_name = None

    PDS = PushDataSource(blue_api['url'], blue_api['apikey'])

    ds_list = PDS.getDataSourceList()
    ds_found = False
    for ds in ds_list:
        if ds['SourceID'] == datasource_id:
            ds_found = True
            print(f"Data source: {ds}")
            break

    if not ds_found:
        raise Exception(f"Data source ID {datasource_id} not found")

    db_list = PDS.getDataBlockInformation(datasource_id)
    for db in db_list:
        if db['ConnectorType'] == 'CSVFile':
            # Use this data block
            print(f"Data block: {db}")
            datablock_name = db['DataBlockName']

    if datablock_name is None:
        raise Exception(f"No CSV data block found in data source {datasource_id}")

    if PDS.RegisterImport(datasource_id):
        status = 0
        print("The process was started")
        bar = progressbar.ProgressBar(maxval=100, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        bar.start()
        if PDS.PushObjectDataV2(datablock_name, csv_file):
            bar.update(PDS.GetProgressStatus())
            if PDS.PrepareDataToFinzalizeImportV2():
                bar.update(PDS.GetProgressStatus())
                if PDS.FinalizeImport():
                    status = PDS.GetProgressStatus()
                    print(f"PDS.GetProgressStatus : {status}")
                    bar.update(status)
        bar.finish()
        if status == 100:
            print("The datasource has updated successfully")
        else:
            print("You have an error please check the logs from Blue")

if __name__ == '__main__':
    main()
