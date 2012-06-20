import os
import hashlib
import tempfile
import shutil
from nose import with_setup
from nose.tools import assert_true
from nose.tools import assert_false
from nose.tools import assert_equal
from nose.tools import assert_not_equal
from nose.tools import assert_raises

from nxdrive.client import LocalClient
from nxdrive.client import NotFound


LOCAL_TEST_FOLDER = None
TEST_WORKSPACE = None
lcclient = None

EMPTY_DIGEST = hashlib.md5().hexdigest()
SOME_TEXT_CONTENT = "Some text content."
SOME_TEXT_DIGEST = hashlib.md5(SOME_TEXT_CONTENT).hexdigest()


def setup_temp_folder():
    global lcclient, LOCAL_TEST_FOLDER, TEST_WORKSPACE
    LOCAL_TEST_FOLDER = tempfile.mkdtemp('-nuxeo-drive-tests')
    lcclient = LocalClient(LOCAL_TEST_FOLDER)
    TEST_WORKSPACE = lcclient.make_folder('/', 'Some Workspace')
    assert_true(lcclient.exists(TEST_WORKSPACE))


def teardown_temp_folder():
    if os.path.exists(LOCAL_TEST_FOLDER):
        shutil.rmtree(LOCAL_TEST_FOLDER)


with_temp_folder = with_setup(setup_temp_folder, teardown_temp_folder)


@with_temp_folder
def test_make_documents():
    doc_1 = lcclient.make_file(TEST_WORKSPACE, 'Document 1.txt')
    assert_true(lcclient.exists(doc_1))
    assert_equal(lcclient.get_content(doc_1), "")
    doc_1_info = lcclient.get_info(doc_1)
    assert_equal(doc_1_info.name, 'Document 1.txt')
    assert_equal(doc_1_info.path, doc_1)
    assert_equal(doc_1_info.get_digest(), EMPTY_DIGEST)
    assert_equal(doc_1_info.folderish, False)

    doc_2 = lcclient.make_file(TEST_WORKSPACE, 'Document 2.txt',
                              content=SOME_TEXT_CONTENT)
    assert_true(lcclient.exists(doc_2))
    assert_equal(lcclient.get_content(doc_2), SOME_TEXT_CONTENT)
    doc_2_info = lcclient.get_info(doc_2)
    assert_equal(doc_2_info.name, 'Document 2.txt')
    assert_equal(doc_2_info.path, doc_2)
    assert_equal(doc_2_info.get_digest(), SOME_TEXT_DIGEST)
    assert_equal(doc_2_info.folderish, False)

    lcclient.delete(doc_2)
    assert_true(lcclient.exists(doc_1))
    assert_false(lcclient.exists(doc_2))

    folder_1 = lcclient.make_folder(TEST_WORKSPACE, 'A new folder')
    assert_true(lcclient.exists(folder_1))
    folder_1_info = lcclient.get_info(folder_1)
    assert_equal(folder_1_info.name, 'A new folder')
    assert_equal(folder_1_info.path, folder_1)
    assert_equal(folder_1_info.get_digest(), None)
    assert_equal(folder_1_info.folderish, True)

    doc_3 = lcclient.make_file(folder_1, 'Document 3.txt',
                               content=SOME_TEXT_CONTENT)
    lcclient.delete(folder_1)
    assert_false(lcclient.exists(folder_1))
    assert_false(lcclient.exists(doc_3))


@with_temp_folder
def test_complex_filenames():
    # create another folder with the same title
    title_with_accents = u"\xc7a c'est l'\xe9t\xe9 !"
    folder_1 = lcclient.make_folder(TEST_WORKSPACE, title_with_accents)
    folder_1_info = lcclient.get_info(folder_1)
    assert_equal(folder_1_info.name, title_with_accents)

    # create another folder with the same title
    title_with_accents = u"\xc7a c'est l'\xe9t\xe9 !"
    folder_2 = lcclient.make_folder(TEST_WORKSPACE, title_with_accents)
    folder_2_info = lcclient.get_info(folder_2)
    assert_equal(folder_2_info.name, title_with_accents + "__1")
    assert_not_equal(folder_1, folder_2)

    title_with_accents = u"\xc7a c'est l'\xe9t\xe9 !"
    folder_3 = lcclient.make_folder(TEST_WORKSPACE, title_with_accents)
    folder_3_info = lcclient.get_info(folder_3)
    assert_equal(folder_3_info.name, title_with_accents + "__2")
    assert_not_equal(folder_1, folder_3)

    # Create a file with weird chars
    long_filename = u"\xe9" * 50 + u"%$#!*()[]{}+_-=';:&^" + ".doc"
    file_1 = lcclient.make_file(folder_1, long_filename)
    file_1 = lcclient.get_info(file_1)
    assert_equal(file_1.name, long_filename)
    assert_equal(file_1.path, os.path.join(folder_1_info.path, long_filename))

    # Create a file with invalid chars
    invalid_filename = u"a/b\\c.doc"
    escaped_filename = u"a-b-c.doc"
    file_2 = lcclient.make_file(folder_1, invalid_filename)
    file_2 = lcclient.get_info(file_2)
    assert_equal(file_2.name, escaped_filename)
    assert_equal(file_2.path, folder_1_info.path + '/' + escaped_filename)


@with_temp_folder
def test_missing_file():
    assert_raises(NotFound, lcclient.get_info, '/Something Missing')


@with_temp_folder
def test_get_children_info():
    folder_1 = lcclient.make_folder(TEST_WORKSPACE, 'Folder 1')
    folder_2 = lcclient.make_folder(TEST_WORKSPACE, 'Folder 2')
    file_1 = lcclient.make_file(TEST_WORKSPACE, 'File 1.txt', content="foo\n")

    # not a direct child of TEST_WORKSPACE
    lcclient.make_file(folder_1, 'File 2.txt', content="bar\n")

    workspace_children = lcclient.get_children_info(TEST_WORKSPACE)
    assert_equal(len(workspace_children), 3)
    assert_equal(workspace_children[0].path, file_1)
    assert_equal(workspace_children[1].path, folder_1)
    assert_equal(workspace_children[2].path, folder_2)
