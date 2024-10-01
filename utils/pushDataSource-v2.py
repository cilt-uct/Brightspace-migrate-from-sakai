import requests
import re
import json
import progressbar
import csv

from html import escape

class PushDataSource:
    def __init__(self,BlueWSURL,BlueAPIKey) -> None:
        self.BlueWSURL = BlueWSURL
        self.EndPoint = self.BlueWSURL+"/BlueWebService.svc/file"
        self.BlueAPIKey = BlueAPIKey
        self.TransactionId = ''
        self.DataSourceID = ''

    def GetDataSourceID(self):
        return 0

    # https://github.com/explorance/blue/blob/main/BlueSampleAPIClient/Explorance_Blue_sample_API_Client/BlueWSImporter.cs
    # StartTransaction

    def getDataSourceList(self):
        # print(self)
        payload = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://temp
            <soapenv:Header>
                <tem:APIKeyHeader>""" + self.BlueAPIKey +"""</tem:APIKeyHeader>
            </soapenv:Header>
            <soapenv:Body>
                <tem:BaseRequest />
            </soapenv:Body>
            </soapenv:Envelope>"""

        headers = {
        'Content-Type': 'text/xml; charset=UTF-8',
        'SOAPAction': 'http://tempuri.org/IBlueWebService/GetDataSourceList ',
        }
        print(self.EndPoint)
        # response = requests.get(URL, headers=headers, data=payload)
        response = requests.request("GET", self.EndPoint, headers=headers, data = payload)
        print(response)
        # Write to XML since it's easier to read than the console.
        with open("getdatasourcelist.xml", "wb") as f:
            f.write(response.content)

    # GetDataBlockInformation()
    def GetDataBlockInformation(self):
        API_KEY = ""
        DATASOURCE_ID = "" # Received from step 1 (GetDatasourceList.py)
        payload = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://temp
            <soapenv:Header>
                <tem:APIKeyHeader>{API_KEY}</tem:APIKeyHeader>
                <tem:DatasourceId>{DATASOURCE_ID}</tem:DatasourceId>
            </soapenv:Header>
            <soapenv:Body>
            <tem:BasicRequestDataSourceId />
            </soapenv:Body>
            </soapenv:Envelope>"""
        headers = {
        'Content-Type': 'text/xml; charset=UTF-8',
        'SOAPAction': 'http://tempuri.org/IBlueWebService/GetDataBlockInformation',
        }

        response = requests.request("POST", self.EndPoint, headers=headers, data = payload)
        print(response.content)
        # Write to XML since it's easier to read.
        with open("./output/2. getdatablockinformation.xml", "wb") as f:
            f.write(response.content)

# PDS = PushDataSource("https://ucttest.bluera.com/ucttestWS","b244d2aa-61d3-4974-aaf7-2892f1b54299")
PDS = PushDataSource("https://uct.bluera.com/uct","b244d2aa-61d3-4974-aaf7-2892f1b54299")
# GDS = PushDataSource("https://ucttest.bluera.com/ucttestWS/BlueWebService.svc","b244d2aa-61d3-4974-aaf7-2892f1b54299")
PDS.getDataSourceList()
# getDataSourceList()
