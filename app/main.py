from typing import Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel

import requests
import json
import sys
import base64
import zlib

from fastapi.templating import Jinja2Templates
from requests.auth import HTTPProxyAuth
from typing import Optional

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class QueryInputs(BaseModel):
    template: str
    endpoint: str
    content_type: str
    username: Optional[str]
    password: Optional[str]

app = FastAPI()

@app.post("/")
async def root(request: Request, input: QueryInputs):
    
    #import ipdb; ipdb.set_trace()

    if input.username is None:
        res = requests.get(input.endpoint, verify=False)
    else:
        res = requests.get(input.endpoint, verify=False, auth=(input.username, input.password))
    
    if res.status_code == 200:
        data = json.loads(res.content)
        
        templates = Jinja2Templates(directory="../templates")
        
        response = templates.TemplateResponse(input.template, {"request" : request, "data": data})
        response.headers['content-type'] = f"{input.content_type}; charset=utf-8"
        
        return response
    else:
        return {"error": "Error in the endpoint request"}

@app.post("/generate")
async def generate_get(request: Request, input: QueryInputs):
    template_request_body = json.dumps(dict(input)).encode('utf-8')
    return base64.urlsafe_b64encode(zlib.compress(template_request_body, 9)).decode('ascii')

@app.get("/{input}")
async def get_templated_data(request: Request, input: str):
    
    template_request_body = zlib.decompress(base64.urlsafe_b64decode(input)).decode('utf-8')
    return await root(request, QueryInputs.parse_raw(template_request_body))
