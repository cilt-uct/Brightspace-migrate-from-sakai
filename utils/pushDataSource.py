#! /usr/bin/python3

# Push a CSV into an Explorance Blue data source
# https://jira.cilt.uct.ac.za/browse/AMA-1092
# Temporary home before this is moved into middleware

import requests
import os
import sys
import progressbar
import csv
import logging
import zeep
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuth
import config.logging_config

class PushDataSource:
    def __init__(self,BlueWSURL,BlueAPIKey) -> None:
        self.BlueWSURL = BlueWSURL
        self.EndPoint = self.BlueWSURL+"/BlueWebService.svc/file"
        self.BlueAPIKey = BlueAPIKey
        self.TransactionId = ''
        self.DataSourceID = ''

        logging.getLogger('zeep.wsdl.bindings.soap').setLevel(logging.ERROR)
        self.client = zeep.Client(wsdl=self.BlueWSURL+"/BlueWebService.svc?wsdl")

    def getDataSourceList(self):
        response = self.client.service.GetDataSourceList(_soapheaders={'APIKeyHeader': self.BlueAPIKey})
        ds = response['body']['DataSources']['IDataSource']
        return ds

    def getDataBlockInformation(self, datasource_id):
        response = self.client.service.GetDataBlockInformation(_soapheaders={'APIKeyHeader': self.BlueAPIKey, 'DatasourceId' : datasource_id})
        dbi = response['body']['DataBlockInfoList']['DataBlockInfo']
        return dbi

    def RegisterImport(self,DataSourceID,AbortOnEmpty='true',ReplaceBlueRole='false',ReplaceDataSourceAccessKey='false',ReplaceLanguagePreferences='false'):
        self.DataSourceID = DataSourceID

        response = self.client.service.RegisterImport(
                _soapheaders={'APIKeyHeader': self.BlueAPIKey},
                AbortOnEmpty = AbortOnEmpty,
                DataSourceID = DataSourceID,
                ReplaceBlueRole = ReplaceBlueRole,
                ReplaceDataSourceAccessKey = ReplaceDataSourceAccessKey,
                ReplaceLanguagePreferences = ReplaceLanguagePreferences
        )

        if 'TransactionID' in response['body']:
            self.TransactionId = response['body']['TransactionID']
            return True

        return False

    def PushObjectDataV2(self, DataSourceID, csv_file):

        with open(csv_file, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            Header = "<tem:ColumnNamesList>"
            for fieldname in reader.fieldnames:
                Header += f"<arr:string>{fieldname}</arr:string>"
            Header += "</tem:ColumnNamesList>"

            xml_data  = "<tem:Data>"
            for row in reader:
                xml_data  += "<blue:IDataRow><blue:IDataRowValue>"

                for k, v in row.items():
                    xml_data  += f"<blue:IDataObj><blue:IDataObjValue>{v}</blue:IDataObjValue></blue:IDataObj>"
                xml_data  += "</blue:IDataRowValue></blue:IDataRow>"

            xml_data  += "</tem:Data>"

            TransactionId = self.TransactionId
            DataSourceID = str(DataSourceID)
            Header = str(Header)  # Header should already be a string, but convert it just in case

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

            response = requests.request("POST", self.EndPoint, headers=headers, data=payload.encode("utf-8"))

            if response.status_code==200:
                return True
            else:
                print(response.content)
                self.CancelImport()
                return False

    def PrepareDataToFinzalizeImportV2(self):
        response = self.client.service.PrepareDataToFinzalizeImportV2(
                _soapheaders={'APIKeyHeader': self.BlueAPIKey, 'TransactionID': self.TransactionId}
        )

        if response['body']['Message'] == "Success":
            return True
        else:
            self.CancelImport()
            return False

    def FinalizeImport(self):
        response = self.client.service.FinalizeImport(
                _soapheaders={'APIKeyHeader': self.BlueAPIKey, 'TransactionID': self.TransactionId}
        )

        if response['header']['Message'] == "Success":
            return True
        else:
            self.CancelImport()
            return False

    def CancelImport(self):
        self.client.service.CancelImport(
                _soapheaders={'APIKeyHeader': self.BlueAPIKey, 'TransactionID': self.TransactionId}
        )
        return

    def GetProgressStatus(self):
        response = self.client.service.GetProgressStatus(
                _soapheaders={'APIKeyHeader': self.BlueAPIKey},
                DataSourceId = self.DataSourceID
        )
        return response['body']['ProgressStatus']

#######

def push_datasource(PDS, csv_file, datasource_id):

    datablock_name = None

    ds_list = PDS.getDataSourceList()
    ds_caption = None
    for ds in ds_list:
        if ds['SourceID'] == datasource_id:
            ds_caption = ds['Caption']
            logging.debug(f"Data source: {ds}")
            break

    if ds_caption is None:
        raise Exception(f"Data source ID {datasource_id} not found")

    db_list = PDS.getDataBlockInformation(datasource_id)
    for db in db_list:
        if db['ConnectorType'] == 'CSVFile':
            # Use this data block
            logging.debug(f"Data block: {db}")
            datablock_name = db['DataBlockName']

    if datablock_name is None:
        raise Exception(f"No CSV data block found in data source {datasource_id}")

    logging.info(f"Importing CSV {csv_file} into data source {datasource_id} '{ds_caption}' data block {datablock_name}")

    if PDS.RegisterImport(datasource_id):
        status = 0
        print("The process was started\n")
        bar = progressbar.ProgressBar(maxval=100, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        bar.start()
        if PDS.PushObjectDataV2(datablock_name, csv_file):
            bar.update(PDS.GetProgressStatus())

            if PDS.PrepareDataToFinzalizeImportV2():
                bar.update(PDS.GetProgressStatus())
                if PDS.FinalizeImport():
                    status = PDS.GetProgressStatus()
                    #print(f"PDS.GetProgressStatus : {status}")
                    bar.update(status)

        bar.finish()

        if status == 100:
            print("The datasource has updated successfully")
        else:
            print("You have an error please check the logs from Blue")

def main():

    parser = argparse.ArgumentParser(description="Update an Explorance Blue Data Source from a CSV file",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--id')
    parser.add_argument('--csv')
    parser.add_argument('--dev', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-l', '--list', action='store_true')
    args = vars(parser.parse_args())

    if args['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    blue_source = "BlueTest" if args['dev'] else "Blue"
    blue_api = getAuth(blue_source, ['apikey', 'url'])

    if not blue_api['valid']:
        raise Exception("Missing configuration")

    logging.info(f"Explorance endpoint {blue_api['url']}")
    PDS = PushDataSource(blue_api['url'], blue_api['apikey'])

    # List datasources
    if args['list']:
        ds_list = PDS.getDataSourceList()
        print(f"Datasources:\n{ds_list}")
        return

    # Push a CSV file to a datasource
    # (Live Data9 = Courses Instructors)
    # (Test Data25 = Courses Instructors)

    csv_file = args['csv']
    ds_id = args['id']

    if not csv_file or not ds_id:
        logging.error("Must specify both CSV and ID")
        exit(1)

    if not os.path.exists(csv_file):
        logging.error(f"CSV file {csv_file} not found")
        exit(1)

    push_datasource(PDS, csv_file, ds_id)

if __name__ == '__main__':
    main()
