from datetime import datetime
import json
import logging
import sys

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from SophosInventory import SophosInventory


ADDON_NAME = "sophos_inventory"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_api_key(session_key: str, account_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-sophos_inventory_account",
    )
    account_conf_file = cfm.get_conf("sophos_inventory_account")
    client_id = account_conf_file.get(account_name).get("api_key")
    client_secret = account_conf_file.get(account_name).get("api_key")
    return client_id, client_secret


def validate_input(definition: smi.ValidationDefinition):
    return

class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("trendmicsophos_inventoryro_ddei")
        scheme.description = "trendmicro_sophos_inventoryddei input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        #scheme.add_argument(smi.Argument("name", title="Name", description="Name", required_on_create=True))        
        return scheme
    
    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        # inputs.inputs is a Python dictionary object like:
        # {
        #   "sophos_inventory://<input_name>": {
        #     "account": "<account_name>",
        #     "disabled": "0",
        #     "host": "$decideOnStartup",
        #     "index": "<index_name>",
        #     "interval": "<interval_value>",
        #     "python.version": "python3",
        #   },
        # }
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            logger = logger_for_input(normalized_input_name)
            try:
                session_key = inputs.metadata["session_key"]
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name="sophos_inventory_settings",
                )
                logger.setLevel(log_level)
                log.modular_input_start(logger, normalized_input_name)
                
                
                client_id, client_secret = get_account_api_key(session_key, input_item.get("account"))
                index = input_item.get("index")
                sourcetype = input_item.get("sourcetype")
                if sourcetype == "" or sourcetype == None:
                    sourcetype = "sophos:inventory"
                organization_id = input_item.get("organization_id")
                if not all([client_id, client_secret, index]):
                    logger.error("Missing required credentials")
                    continue
                
                logger.info(f"Initializing Sophos Inventory account: input_name={normalized_input_name}")

                sophos_inventory = SophosInventory(client_id, client_secret)

                try:
                    sophos_inventory.getToken()
                    logger.info("Successfully obtained token from Sophos")
                except Exception as e:
                    logger.error("Failed to obtain access token")
                    log.log_exception(logger, e, msg_before=f"Authentication failed for input {normalized_input_name}")
                    continue

                try:
                    tenants = sophos_inventory.getTenants(organization_id)
                    logger.info("Successfully obtained tenats from Sophos")
                except Exception as e:
                    logger.error("Failed to obtain tenants from Sophos")
                    log.log_exception(logger, e, msg_before=f"Failed getTenants for input {normalized_input_name}")
                    continue

                try:
                    current_time = datetime.utcnow().isoformat()
                    for tenant in tenants:
                        endpoints = sophos_inventory.getEndpointTenant(tenant[0], tenant[1])
                        for endpoint in endpoints:
                            event = smi.Event()
                            event.stanza = input_name
                            event.index = index
                            event.sourcetype = sourcetype
                            event.source = normalized_input_name
                            event.time = current_time
                            event.data = json.dumps(endpoint, ensure_ascii=False, default=str)
                            event_writer.write_event(event)
                    logger.info(f"Successfully ingested {len(tenants)} Sophos tenants into Splunk")
                except Exception as e:
                    logger.error("Failed to obtain endpoints from Sophos")
                    log.log_exception(logger, e, msg_before=f"Failed getTenants for input {normalized_input_name}")
                    continue
                log.modular_input_end(logger, normalized_input_name)
            except Exception as e:
                logger.error("Unexpected error during execution")
                log.log_exception(
                    logger,
                    e,
                    "Error during Sophos ingestion",
                    msg_before=f"Exception raised while ingesting data for input {normalized_input_name}"
                )

if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)