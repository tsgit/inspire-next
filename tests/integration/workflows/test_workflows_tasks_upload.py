# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE.
# Copyright (C) 2018 CERN.
#
# INSPIRE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import absolute_import, division, print_function

from mock import MagicMock, patch
from flask import current_app

from invenio_workflows import workflow_object_class

from inspirehep.modules.records.api import InspireRecord, RecordMetadata

from factories.db.invenio_records import TestRecordMetadata


# FIXME: otherwise this task is not found by Celery.
from inspirehep.modules.orcid.tasks import orcid_push  # noqa: F401
from inspirehep.modules.workflows.tasks.upload import (
    is_stale_data,
    store_root,
    store_record,
)
from inspirehep.modules.workflows.utils import (
    insert_wf_record_source,
    read_wf_record_source,
)


@patch('inspirehep.modules.orcid.domain_models.OrcidPusher')
def test_store_record_does_not_raise_in_the_orcid_receiver(mock_attempt_push, app):
    config = {
        'FEATURE_FLAG_ENABLE_ORCID_PUSH': True,
        'RECORDS_SKIP_FILES': False,
    }
    eng = MagicMock(workflow_definition=MagicMock(data_type='hep'))

    with patch.dict(current_app.config, config):
        obj = workflow_object_class.create({
            '$schema': 'http://localhost:5000/schemas/records/hep.json',
            '_collections': [
                'Literature',
            ],
            'authors': [
                {
                    'full_name': 'Patra, Asim',
                    'ids': [
                        {
                            'schema': 'ORCID',
                            'value': '0000-0003-1166-2790',
                        },
                    ],
                },
            ],
            'document_type': [
                'article',
            ],
            'titles': [
                {'title': 'title'},
            ],
        })

        store_record(obj, eng)  # Does not raise.


def test_store_root_new_record(workflow_app):
    config = {
        'FEATURE_FLAG_ENABLE_MERGER': True
    }
    eng = MagicMock(workflow_definition=MagicMock(data_type='hep'))

    with patch.dict(current_app.config, config):
        head = TestRecordMetadata.create_from_kwargs(index=False, has_pid=False)
        head_uuid = head.record_metadata.id
        record = head.record_metadata.json

        obj = workflow_object_class.create(record)

        root = {
            'version': 'original',
            'acquisition_source': {'source': 'arXiv'}
        }

        extra_data = {
            'head_uuid': str(head_uuid),
            'merger_root': root,
        }

        obj.extra_data = extra_data

        store_root(obj, eng)

        root_entry = read_wf_record_source(head_uuid, 'arxiv')

        assert root_entry.json == root


def test_store_root_update_record(workflow_app):
    config = {
        'FEATURE_FLAG_ENABLE_MERGER': True
    }
    eng = MagicMock(workflow_definition=MagicMock(data_type='hep'))

    with patch.dict(current_app.config, config):
        head = TestRecordMetadata.create_from_kwargs(index=False, has_pid=False)
        head_uuid = head.record_metadata.id
        record = head.record_metadata.json

        original_root = {
            'version': 'original',
            'acquisition_source': {'source': 'arXiv'},
        }

        update_root = {
            'version': 'updated',
            'acquisition_source': {'source': 'arXiv'},
        }

        insert_wf_record_source(json=original_root, record_uuid=head_uuid, source='arxiv')

        obj = workflow_object_class.create(record)

        extra_data = {
            'head_uuid': str(head_uuid),
            'merger_root': update_root,
        }

        obj.extra_data = extra_data

        store_root(obj, eng)

        root_entry = read_wf_record_source(head_uuid, 'arxiv')

        assert root_entry.json == update_root


def test_is_stale_data_is_false(workflow_app):
    head = TestRecordMetadata.create_from_kwargs(index=False, has_pid=False)
    obj = workflow_object_class.create({})
    obj.extra_data['is-update'] = True
    obj.extra_data['head_uuid'] = head.record_metadata.id
    obj.extra_data['head_version_id'] = head.record_metadata.version_id

    assert is_stale_data(obj, None) is False


def test_is_stale_data_is_true(workflow_app):
    head = TestRecordMetadata.create_from_kwargs(index=False, has_pid=False)
    obj = workflow_object_class.create({})
    obj.extra_data['is-update'] = True
    obj.extra_data['head_uuid'] = head.record_metadata.id
    obj.extra_data['head_version_id'] = head.record_metadata.version_id - 1

    assert is_stale_data(obj, None)


def test_is_stale_data_returns_false_if_is_update_is_falsy(workflow_app):
    TestRecordMetadata.create_from_kwargs(index=False, has_pid=False)
    obj = workflow_object_class.create({})
    assert is_stale_data(obj, None) is False


def test_regression_store_record_does_not_commit_when_error(workflow_app):
    data = {
        '$schema': 'http://localhost:5000/schemas/records/hep.json',
        '_collections': ['Literature'],
        'document_type': ['article'],
        'titles': [{'title': 'title'}],
    }
    eng = MagicMock(workflow_definition=MagicMock(data_type='hep'))

    obj = workflow_object_class.create(data)

    record_count = RecordMetadata.query.count()
    assert record_count == 0

    with patch.object(
        InspireRecord,
        'download_documents_and_figures',
        side_effect=Exception
    ):
        # pytest.raises catches the exception and makes the test passing immediately
        try:
            store_record(obj, eng)
        except Exception:
            record_count = RecordMetadata.query.count()
            assert record_count == 0