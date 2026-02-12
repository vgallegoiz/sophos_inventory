import json
import requests

class SophosInventory:
    def __init__(self, client_id, client_secret):
        self.access_token = None
        self.client_id = client_id
        self.client_secret = client_secret

    def getToken(self):
        url = "https://id.sophos.com/api/v2/oauth2/token"
        payload = f"grant_type=client_credentials&client_id={self.client_id}&client_secret={self.client_secret}&scope=token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        try:
            response = requests.post(url=url, headers=headers, data=payload)
        except Exception as e:
            print(e)
            return
        try:
            response_json = response.json()
        except Exception as e:
            print(e)
            return
        self.access_token = response_json["access_token"]

    def getTenants(self, organization_id):
        url = "https://api.central.sophos.com/organization/v1/tenants"
        headers = {
            'X-Organization-ID': f"{organization_id}",
            'Authorization': f"Bearer {self.access_token}"
        }
        try:
            response = requests.get(url=url, headers=headers)
        except Exception as e:
            print(e)
            return
        try:
            response_json = response.json()
        except Exception as e:
            print(e)
            return
        tenants = []
        for tenant in response_json["items"]:
            tenant_id = tenant["id"]
            region_code = tenant["dataRegion"]
            tenants.append([tenant_id, region_code])
        return tenants

    def getEndpointTenant(self, tenant_id, region_code):
        url = f"https://api-{region_code}.central.sophos.com/endpoint/v1/endpoints"
        headers = {
            'X-Tenant-ID': f"{tenant_id}",
            'Authorization': f"Bearer {self.access_token}"
        }
        try: 
            response = requests.get(url=url, headers=headers)
        except Exception as e: 
            print(e)
            return
        try:
            response_json = response.json()
        except Exception as e:
            print(e)
            return
        
        endpoints = []
        for item in response_json["items"]:
            endpoints.append(item)
        return endpoints