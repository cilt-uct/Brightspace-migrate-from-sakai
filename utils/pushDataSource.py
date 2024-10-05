#! /usr/bin/python3

# Push a CSV into an Explorance Blue data source
# https://jira.cilt.uct.ac.za/browse/AMA-1092
# Temporary home before this is moved into middleware

import os
import sys
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

        self.BlueAPIKey = BlueAPIKey
        self.TransactionId = ''
        self.DataSourceID = ''

        logging.getLogger('zeep.wsdl.bindings.soap').setLevel(logging.ERROR)
        self.client = zeep.Client(wsdl=BlueWSURL+"/BlueWebService.svc?wsdl")

        self.client.set_ns_prefix("tem", "http://tempuri.org/")
        self.client.set_ns_prefix("arr", "http://schemas.microsoft.com/2003/10/Serialization/Arrays")
        self.client.set_ns_prefix("blue", "http://schemas.datacontract.org/2004/07/Blue.Integration")

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

    def PushObjectDataV2(self, datablock_name, csv_file):

        with open(csv_file, encoding="utf-8") as file:
            d_reader = csv.DictReader(file)
            fieldnames = d_reader.fieldnames

            array_of_string_type = self.client.get_type("arr:ArrayOfstring")
            array_of_datarow_type = self.client.get_type("blue:ArrayOfIDataRow")
            array_of_dataobj_type = self.client.get_type("blue:ArrayOfIDataObj")
            datarow_type = self.client.get_type("blue:IDataRow")
            dataobj_type = self.client.get_type("blue:IDataObj")

            row_list = []
            for row in d_reader:
                row_obj = []
                for k, v in row.items():
                    row_obj.append(dataobj_type(v))
                row_list.append(datarow_type(array_of_dataobj_type(row_obj)))

            response = self.client.service.PushObjectDataV2(
                _soapheaders={
                    'APIKeyHeader': self.BlueAPIKey,
                    'TransactionId': self.TransactionId,
                    'DataBlockName': datablock_name,
                    'ColumnNamesList': array_of_string_type(fieldnames)
                },
                Data = array_of_datarow_type(row_list)
            )

            if response['body']['Message'] == "Success":
                return True
            else:
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
        logging.info(f"Starting import to data source {datasource_id} block {datablock_name}")
        if PDS.PushObjectDataV2(datablock_name, csv_file):
            if PDS.PrepareDataToFinzalizeImportV2():
                if PDS.FinalizeImport():
                    status = PDS.GetProgressStatus()

        if status == 100:
            logging.info(f"Data source {datasource_id} updated successfully")
        else:
            logging.error(f"You have an error, please check the logs from Blue. Status={status}")

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
