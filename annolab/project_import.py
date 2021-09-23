import json
from http import HTTPStatus
from logging import Logger
import os
import re
import shutil
import tempfile
from uuid import uuid4
from typing import Union, List

import jsonlines
from requests.exceptions import HTTPError

from annolab import Project

logger = Logger(__name__)

class ProjectImport:

  source_file: str = None
  bounds_file: str = None
  annotations_file: str = None
  layers_file: str = None
  relations_file: str = None
  schemas_file: str = None
  atntypes_file: str = None

  def __init__(
    self,
    export_filepath: str,
    project: Project,
    groupId: Union[str, int]
  ):
    self.export_filepath = export_filepath
    self.project = project
    self.groupId = groupId
    self.unpack_target_dir = os.path.join(tempfile.gettempdir(), str(uuid4()))


  def unzip_export(self):
    if not os.path.exists(self.unpack_target_dir):
      os.mkdir(self.unpack_target_dir)

    shutil.unpack_archive(self.export_filepath, self.unpack_target_dir)
    self.__find_entity_files()
    self.import_sources()

    shutil.rmtree(self.unpack_target_dir, ignore_errors=True)


  def import_sources(self):
    filepath = os.path.join(self.unpack_target_dir, self.source_file)
    with jsonlines.open(filepath) as sources:
      for source in sources:
        self.create_source(source)


  def create_source(self, source: dict):
    try:
      if source['type'] == 'text':
        self.project.create_text_source(source['sourceName'], source['text'], source['directoryName'])
      elif source['type'] == 'pdf':
        pdf_filepath = os.path.join(self.unpack_target_dir, source['directoryName'], source['sourceName'])
        text_bounds = self.__find_source_bounds(source['sourceId'])
        if (text_bounds is None):
          logger.error(f'Unable to find text bounds for {source["sourceId"]}')

        self.project.create_pdf_source(
          pdf_filepath,
          source['sourceName'],
          source['directoryName'],
          ocr=False,
          sourceText=source['text'],
          textBounds=text_bounds['textBounds']
        )
    except HTTPError as e:
      if (e.response.status_code == HTTPStatus.CONFLICT):
        logger.warning(f'Source {source.get("directory")}/{source.get("sourceName")} already exists. Skipping')
      else:
        raise e


  def __find_entity_files(self):
    contents = os.listdir(self.unpack_target_dir)
    export_files = list(filter(lambda item: re.match('.*jsonl', item), contents))

    self.source_file = self.__find_file(export_files, '.*\.sources\.jsonl')
    self.bounds_file = self.__find_file(export_files, '.*\.text-bounds\.jsonl')
    self.annotations_file = self.__find_file(export_files, '.*\.annotations\.jsonl')
    self.layers_file = self.__find_file(export_files, '.*\.layers\.jsonl')
    self.relations_file = self.__find_file(export_files, '.*\.relations\.jsonl')
    self.schemas_file = self.__find_file(export_files, '.*\.schemas\.jsonl')
    self.atntypes_file = self.__find_file(export_files, '.*\.atntypes\.jsonl')

    if (self.source_file is None):
      raise Exception('Sources missing from export. Ensure to make the export request using includeSources=True.')
    if (self.bounds_file is None):
      raise Exception('Text Bounds missing from export. Ensure to make the export request using includeTextBounds=True.')
    if (self.schemas_file is None):
      raise Exception('Schemas missing from export. Ensure to make the export request using includeSchemas=True.')
    if (self.atntypes_file is None):
      raise Exception('Annotation Types missing from export. Ensure to make the export request using includeSchemas=True.')
    if (self.annotations_file is None):
      raise Exception('Annotations missing from export.')
    if (self.layers_file is None):
      raise Exception('Layers missing from export.')
    if (self.relations_file is None):
      raise Exception('Relations missing from export.')


  def __find_file(self, file_list: List[str], pattern: str):
    for filename in file_list:
      if (re.match(pattern, filename) is not None):
        return filename

    return None

  
  def __find_source_bounds(self, source_id: int):
    """Finds the source bounds of a source by iterating through the bounds file for the source id.

      *** Note: This is a highly inefficient v0.1 implementation ***
      The bounds file is redundantly iterated through every time.
      Perhaps the file should be pre-parsed, storing the byte offset of every source id to form
      an index?
    """
    filepath = os.path.join(self.unpack_target_dir, self.bounds_file)
    with jsonlines.open(filepath) as text_bounds:
      for bounds in text_bounds:
        if (bounds['sourceId'] == source_id):
          return bounds

    return None