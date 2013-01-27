import hashlib
from nxdrive.client import NotFound
from nxdrive.tests.common import IntegrationTestCase


DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX = 'defaultFileSystemItemFactory/default/'

class TestIntegrationRemoteFileSystemClient(IntegrationTestCase):

    #
    # Test the API common with the local client API
    #

    def test_get_info(self):
        remote_document_client = self.remote_document_client_1
        remote_file_system_client = self.remote_file_system_client_1

        # Check file info
        file_uid = remote_document_client.make_file(self.workspace,
            'Document 1.txt', content="Content of doc 1.")
        fs_item_id = DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + file_uid
        info = remote_file_system_client.get_info(fs_item_id)
        self.assertEquals(info.name, 'Document 1.txt')
        self.assertEquals(info.uid, fs_item_id)
        self.assertEquals(info.parent_uid,
            DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + self.workspace)
        self.assertFalse(info.folderish)
        digestAlgorithm = info.digestAlgorithm
        self.assertEquals(digestAlgorithm, 'MD5')
        # TODO: use digest algorithm to hash content
        digest = hashlib.md5("Content of doc 1.").hexdigest()
        self.assertEquals(info.digest, digest)
        self.assertEquals(info.download_url,
            'nxbigfile/default/' + file_uid + '/blobholder:0/Document%201.txt')

        # Check folder info
        folder_uid = remote_document_client.make_folder(self.workspace,
            'Folder 1')
        fs_item_id = DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + folder_uid
        info = remote_file_system_client.get_info(fs_item_id)
        self.assertEquals(info.name, 'Folder 1')
        self.assertEquals(info.uid, fs_item_id)
        self.assertEquals(info.parent_uid,
            DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + self.workspace)
        self.assertTrue(info.folderish)
        self.assertIsNone(info.digestAlgorithm)
        self.assertIsNone(info.digest)
        self.assertIsNone(info.download_url)

        # Check non existing file info
        fs_item_id = DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + 'fakeId'
        self.assertRaises(NotFound,
            remote_file_system_client.get_info, fs_item_id)
        self.assertIsNone(
            remote_file_system_client.get_info(fs_item_id,
                raise_if_missing=False))

    def test_get_content(self):
        remote_document_client = self.remote_document_client_1
        remote_file_system_client = self.remote_file_system_client_1

        # Check file with content
        doc_uid = remote_document_client.make_file(self.workspace,
            'Document 1.txt', content="Content of doc 1.")
        fs_item_id = DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + doc_uid
        self.assertEquals(remote_file_system_client.get_content(fs_item_id),
            "Content of doc 1.")

        # Check file without content
        doc_uid = remote_document_client.make_file(self.workspace,
            'Document 2.txt')
        fs_item_id = DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + doc_uid
        self.assertRaises(NotFound,
            remote_file_system_client.get_content, fs_item_id)

    def test_get_children_info(self):
        # TODO
        pass

    def test_make_folder(self):
        # TODO
        pass

    def test_make_file(self):
        # TODO
        pass

    def test_update_content(self):
        #TODO
        pass

    def test_delete(self):
        # TODO
        pass

    def test_exists(self):
        remote_document_client = self.remote_document_client_1
        remote_file_system_client = self.remote_file_system_client_1

        # Check existing file system item
        doc_uid = remote_document_client.make_file(self.workspace,
            'Document 1.txt', content="Content of doc 1.")
        fs_item_id = DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + doc_uid
        self.assertTrue(remote_file_system_client.exists(fs_item_id))

        # Check non existing file system item (non existing document)
        fs_item_id = DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + 'fakeId'
        self.assertFalse(remote_file_system_client.exists(fs_item_id))

        # Check non existing file system item (document without content)
        doc_uid = remote_document_client.make_file(self.workspace,
            'Document 2.txt')
        fs_item_id = DEFAULT_FILE_SYSTEM_ITEM_ID_PREFIX + doc_uid
        self.assertFalse(remote_file_system_client.exists(fs_item_id))

    # TODO: probably to be replaced by test_can_rename, test_can_update,
    # test_can_delete, test_can_create_child
    def test_check_writable(self):
        # TODO
        pass

    #
    # Test the API specific to the remote file system client
    #

    def test_get_fs_item(self):
        # TODO
        pass