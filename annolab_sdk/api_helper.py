from typing import Dict, Any
import requests
from urllib import parse
import logging
from requests.models import Response

import annolab_sdk

class ApiHelper(object):

  def __init__(
    self,
    api_key = None,
    api_url = 'http://localhost:8080',
  ):
    self.api_url = api_url
    self.api_key = api_key or annolab_sdk.api_key


  @property
  def __auth_header(self, key: str = None):
    key = key or self.api_key
    return { 'Authorization': f'Api-Key {key}' }


  def get_request(self, path: str, body: Dict[str, Any] = None) -> Response:
    resp = requests.get(
      parse.urljoin(self.api_url, path),
      headers=self.__auth_header,
      json=body
    )

    self.__handle_non_2xx_response(resp)

    return resp


  def post_request(self, path: str, body: Dict[str, Any] = None):
    resp = requests.post(
      parse.urljoin(self.api_url, path),
      headers=self.__auth_header,
      json=body
    )

    self.__handle_non_2xx_response(resp)

    return resp


  def __handle_non_2xx_response(self, resp: Response):
    if (resp.status_code >= 300):
      try:
        resp_body = resp.json()
      except:
        resp_body = {}

      message = resp_body['message'] if 'message' in resp_body else 'Unknown Error'

      logging.error(f'{resp.request.method} {resp.request.path_url} failed with message: {message}')
      resp.raise_for_status()