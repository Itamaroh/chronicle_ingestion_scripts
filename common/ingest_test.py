# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Unit test file for ingest.py file."""

import os
import sys

# copybara:insert(imports) import unittest
from unittest import mock

# copybara:strip_begin(imports)
from google3.testing.pybase import googletest
# copybara:strip_end

# Path to common framework.
INGESTION_SCRIPTS_PATH = "google3.third_party.chronicle.ingestion_scripts.common"

sys.path.append(
    os.path.sep.join(
        [os.path.realpath(os.path.dirname(__file__)), "..", "common"]))

with mock.patch(
    f"{INGESTION_SCRIPTS_PATH}.utils.get_env_var") as mocked_get_env_var:
  mocked_get_env_var.return_value = "{}"
  # Disabling the import error because ingest.py file fetches value of some
  # environment variables at the start of the file. Hence, this file will need
  # to be imported after mocking the function `get_env_var()`
  # copybara:strip_begin(imports)
  from google3.third_party.chronicle.ingestion_scripts.common import ingest  # pylint: disable=g-import-not-at-top
  # copybara:strip_end


# copybara:insert(imports) class TestIngestMethod(unittest.TestCase):
class TestIngestMethod(googletest.TestCase):
  """Unit test class for ingest."""

  @mock.patch(f"{INGESTION_SCRIPTS_PATH}.ingest._send_logs_to_chronicle")
  @mock.patch(f"{INGESTION_SCRIPTS_PATH}.ingest.json")
  @mock.patch(f"{INGESTION_SCRIPTS_PATH}.ingest.initialize_http_session")
  def test_ingest(self, mocked_initialize_http_session, mocked_json,  # pylint: disable=unused-argument
                  mocked_send_logs_to_chronicle):
    """Test case to verify the successful scenario of ingest function.

    Args:
      mocked_initialize_http_session (mock.Mock): Mocked object of
        initialize_http_session() method.
      mocked_json (mock.Mock): Mocked object of json module.
      mocked_send_logs_to_chronicle (mock.Mock): Mocked object of
        send_logs_to_chronicle() method.

    Asserts:
      Validates that ingest() method is called once and no error occurred while
      calling send_logs_to_chronicle() method.
      Validates that send_logs_to_chronicle() method is called once.
    """
    mocked_json.dumps.return_value = "{}"
    assert ingest.ingest(["data"], "log_type") is None
    assert mocked_send_logs_to_chronicle.call_count == 1

  @mock.patch(f"{INGESTION_SCRIPTS_PATH}.ingest._send_logs_to_chronicle")
  @mock.patch(f"{INGESTION_SCRIPTS_PATH}.ingest.sys")
  @mock.patch(f"{INGESTION_SCRIPTS_PATH}.ingest.initialize_http_session")
  def test_ingest_when_data_greater_than_1_mb(self,
                                              mocked_initialize_http_session,
                                              mocked_sys,
                                              mocked_send_logs_to_chronicle):
    """Test case to verify the execution of ingest function when the size of data is greater than 1MB.

    Args:
      mocked_initialize_http_session (mock.Mock): Mocked object of
        initialize_http_session() method.
      mocked_sys (mock.Mock): Mocked object of sys module.
      mocked_send_logs_to_chronicle (mock.Mock): Mocked object of
        send_logs_to_chronicle() method.

    Asserts:
      Validates that ingest() method is called once and no error occurred while
      calling send_logs_to_chronicle() method.
      Validates that send_logs_to_chronicle() method is called once.
    """
    mocked_sys.getsizeof.side_effect = [950000, 950000, 10, 10]
    assert ingest.ingest(["data"], "log_type") is None
    assert mocked_initialize_http_session.call_count == 1
    assert mocked_send_logs_to_chronicle.call_count == 2

  def test_send_logs_to_chronicle_for_success(self):
    """Test case to verify the successful ingestion of logs to the Chronicle.

    Asserts:
      Validates the execution of send_logs_to_chronicle() method.
      Validates the session sends the request to chronicle.
      Validates the json() object is fetched from the response.
      Validates the raise_for_status() object is executed for the request.
    """
    mocked_http_session = mock.MagicMock()
    mocked_response = mock.MagicMock()
    mocked_http_session.request.return_value = mocked_response
    mock_body = {
        "entries": [{"logText": '{"id": "test_id"}'}]
    }
    assert ingest._send_logs_to_chronicle(mocked_http_session, mock_body,
                                          "region") is None
    assert mocked_http_session.request.call_count == 1
    assert mocked_response.json.call_count == 1
    assert mocked_response.raise_for_status.call_count == 1

  def test_send_logs_to_chronicle_for_failure(self):
    """Test case to verify the failure of ingestion of logs to the Chronicle.

    Asserts:
      Validates the execution of send_logs_to_chronicle() method.
      Validates the session sends the request to chronicle.
      Validates the json() object is fetched from the response.
      Validates the raise_for_status() object is executed for the request.
    """
    mocked_http_session = mock.MagicMock()
    mocked_response = mock.MagicMock()
    mocked_response.raise_for_status.side_effect = Exception()
    mocked_http_session.request.return_value = mocked_response
    mock_body = {
        "entries": [{"logText": '{"id": "test_id"}'}]
    }
    with self.assertRaises(RuntimeError):
      assert ingest._send_logs_to_chronicle(mocked_http_session, mock_body,
                                            "region") is None
    assert mocked_http_session.request.call_count == 1
    assert mocked_response.json.call_count == 1
    assert mocked_response.raise_for_status.call_count == 1
