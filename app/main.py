from tkinter.messagebox import NO
from typing import Optional, List

from fastapi import FastAPI, Request
from pydantic import BaseModel, HttpUrl

from async_lru import alru_cache

import logging

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
logger = logging.getLogger("fastapi")
#https://dev.to/tomas223/logging-tracing-in-python-fastapi-with-opencensus-a-azure-2jcm

class QueryInputs(BaseModel):
    template: str
    endpoint: HttpUrl
    content_type: str
    payload: Optional[str]
    username: Optional[str]
    password: Optional[str]

class Endpoint(BaseModel):
    def __hash__(self):  # make hashable BaseModel subclass
        return hash((type(self),) + tuple(self.__dict__.values()))    
    url: HttpUrl
    key: str
    payload: Optional[str]
    username: Optional[str]
    password: Optional[str]

class MultiQueryInputs(BaseModel):
    template: str
    endpoints: List[Endpoint]
    content_type: str

app = FastAPI()

@alru_cache
async def _read_get_endpoint(endpoint: Endpoint) -> str:

    headers = {
        'Content-Type': 'application/json'
    }

    if endpoint.username is not None and len(endpoint.username) > 0: 
        return requests.get(endpoint.url, auth=(endpoint.username,endpoint.password), data=endpoint.payload, headers=headers, verify=False)
    else:
        return requests.get(endpoint.url, verify=False, data=endpoint.payload, headers=headers)

@app.post("/")
async def root(request: Request, input: QueryInputs):
    """Esta función se encarga de realizar la consulta a la API y devolver el resultado en formato según una plantilla

    Args:
        request (Request): petición HTTP
        input (QueryInputs): Objeto con la petición al API y la plantilla a utilizar

    Returns:
        response: Respuesta formateada en formato según la plantilla
    """
    endpoint = Endpoint(url=input.endpoint, key="data", username=input.username, password=input.password, payload=input.payload)

    res = await _read_get_endpoint(endpoint)
    
    logger.info(_read_get_endpoint.cache_info())

    if res.status_code == 200:
        data = json.loads(res.content)
        
        templates = Jinja2Templates(directory="../templates")
        
        response = templates.TemplateResponse(input.template, {"request" : request, "data": data})
        response.headers['content-type'] = f"{input.content_type}; charset=utf-8"
        
        return response
    else:
        return {"error": "Error in the endpoint request"}

@app.post("/multiple")
async def multiple(request: Request, input: MultiQueryInputs):
    
    #import ipdb; ipdb.set_trace()

    data = {"request" : request} 
    flag_error = False

    for endpoint in input.endpoints:
        res = await _read_get_endpoint(endpoint)
        
        if res.status_code == 200:
            data[endpoint.key] = json.loads(res.content)
        else:
            flag_error = True

        #logger.info(_read_get_endpoint.cache_info())

    if not flag_error:
        templates = Jinja2Templates(directory="../templates")
        
        response = templates.TemplateResponse(input.template, data)
        response.headers['content-type'] = f"{input.content_type}; charset=utf-8"
        
        return response
    else:
        return {"error": "Error in the endpoint request"}

@app.post("/generate")
async def generate_get(request: Request):
    input_json = await request.json()
    template_request_body = json.dumps(input_json).encode('utf-8')
    return base64.urlsafe_b64encode(zlib.compress(template_request_body, 9)).decode('ascii')

@app.get("/{input}")
async def get_templated_data(request: Request, input: str):
    
    template_request_body = zlib.decompress(base64.urlsafe_b64decode(input)).decode('utf-8')
    if 'endpoints' in template_request_body:
        return await multiple(request, MultiQueryInputs.parse_raw(template_request_body))
    else:
        return await root(request, QueryInputs.parse_raw(template_request_body))
