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

    def PushObjectDataV2(self,DataSourceID):
        # print(f"THIS IS TRANS AC ID: {self.TransactionId}")
        # with open("C:/Users/laithdodin/Python_Projects/BlueWebServices/UCT Sandbox/Data.json") as file:
        with open("courses-instructors.20240925_1518.csv") as file:
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
                                    <blue:IDataRow>
                                        <blue:IDataRowValue>
                                            <blue:IDataObj>
                                                <blue:IDataObjValue>{row['Identifier']}</blue:IDataObjValue>
                                            </blue:IDataObj>
                                            <blue:IDataObj>
                                                <blue:IDataObjValue>{row['User_UserName']}</blue:IDataObjValue>
                                            </blue:IDataObj>
                                            <blue:IDataObj>
                                                <blue:IDataObjValue>{row['User_DisplayName']}</blue:IDataObjValue>
                                            </blue:IDataObj>
                                            <blue:IDataObj>
                                                <blue:IDataObjValue>{row['Role_Id']}</blue:IDataObjValue>
                                            </blue:IDataObj>
                                            <blue:IDataObj>
                                                <blue:IDataObjValue>{row['Role_Name']}</blue:IDataObjValue>
                                            </blue:IDataObj>
                                        </blue:IDataRowValue>
                                    </blue:IDataRow>
                                </tem:DataObjectTransferRequestV2>
                            </soapenv:Body>
                            </soapenv:Envelope>"""

            headers = {
                'Content-Type': 'text/xml;charset=UTF-8',
                'SOAPAction': '"http://tempuri.org/IBlueWebService/PushObjectDataV2"'
                }

            response = requests.request("POST", self.EndPoint, headers=headers, data = payload)
            # print(f"self.BlueAPIKey APIKEY : {self.BlueAPIKey}")
            # print(f"PushObjectDataV2 payload : {payload}")
            # print(f"PushObjectDataV2 response : {response}")
            # print(f"PushObjectDataV2  response.content : {response.content}")
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
        # print(f"GetProgressStatus : {payload}")
        response = requests.request("POST", self.EndPoint, headers=headers, data = payload)
        # print(f"GetProgressStatus : {response}")
        if response.status_code==200:
            m = re.search('<ProgressStatus>(.+?)</ProgressStatus>', response.text)
            if m:
                return int(m.group(1))
        return False



PDS = PushDataSource("https://ucttest.bluera.com/ucttestWS","b244d2aa-61d3-4974-aaf7-2892f1b54299")

# https://uct.bluera.com/uctWS//BlueWebService.svc
#Data137 => BlueNote Test WS
if PDS.RegisterImport("Data23"):
    status = 0
    print("The process was started")
    bar = progressbar.ProgressBar(maxval=100, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()
    if PDS.PushObjectDataV2("WSTest"):
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
