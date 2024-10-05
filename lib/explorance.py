# Explorance Blue SOAP webservices

import csv
import logging
import zeep

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
            return True

        logging.error(f"You have an error, please check the logs from Blue. Status={status}")
        return False

    logging.error("Failed to register data source import")
    return False
