/*
 * (C) Copyright 2012 Nuxeo SA (http://nuxeo.com/) and contributors.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the GNU Lesser General Public License
 * (LGPL) version 2.1 which accompanies this distribution, and is available at
 * http://www.gnu.org/licenses/lgpl.html
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * Contributors:
 *     Antoine Taillefer <ataillefer@nuxeo.com>
 */
package org.nuxeo.drive.service.impl;

import java.security.Principal;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.nuxeo.drive.adapter.FileSystemItem;
import org.nuxeo.drive.adapter.FolderItem;
import org.nuxeo.drive.adapter.impl.DefaultSyncRootFolderItem;
import org.nuxeo.drive.service.FileSystemItemAdapterService;
import org.nuxeo.drive.service.FileSystemItemFactory;
import org.nuxeo.drive.service.NuxeoDriveManager;
import org.nuxeo.drive.service.SynchronizationRoots;
import org.nuxeo.ecm.core.api.ClientException;
import org.nuxeo.ecm.core.api.DocumentModel;
import org.nuxeo.ecm.core.api.LifeCycleConstants;
import org.nuxeo.runtime.api.Framework;

/**
 * Default {@link FileSystemItemFactory} for a synchronization root
 * {@link FolderItem}.
 *
 * @author Antoine Taillefer
 */
public class DefaultSyncRootFolderItemFactory extends
        DefaultFileSystemItemFactory {

    private static final Log log = LogFactory.getLog(DefaultSyncRootFolderItemFactory.class);

    /**
     * Prevent from instantiating class as it should only be done by
     * {@link FileSystemItemFactoryDescriptor#getFactory()}.
     */
    protected DefaultSyncRootFolderItemFactory() {
    }

    @Override
    public FileSystemItem getFileSystemItem(DocumentModel doc)
            throws ClientException {
        return getFileSystemItem(doc, false);
    }

    @Override
    public FileSystemItem getFileSystemItem(DocumentModel doc,
            boolean includeDeleted) throws ClientException {
        String userName = doc.getCoreSession().getPrincipal().getName();
        return getFileSystemItem(
                doc,
                getFileSystemItemAdapterService().getTopLevelFolderItemFactory().getSyncRootParentFolderItemId(
                        userName), includeDeleted);
    }

    @Override
    public FileSystemItem getFileSystemItem(DocumentModel doc, String parentId)
            throws ClientException {
        return getFileSystemItem(doc, parentId, false);
    }

    @Override
    public FileSystemItem getFileSystemItem(DocumentModel doc, String parentId,
            boolean includeDeleted) throws ClientException {
        if (!includeDeleted
                && LifeCycleConstants.DELETED_STATE.equals(doc.getCurrentLifeCycleState())) {
            log.debug(String.format(
                    "Document %s is in the '%s' life cycle state, it cannot be adapted"
                            + " as a FileSystemItem => returning null.",
                    doc.getId(), LifeCycleConstants.DELETED_STATE));
            return null;
        }
        // check that the sync root is currently active
        NuxeoDriveManager nuxeoDriveManager = Framework.getLocalService(NuxeoDriveManager.class);
        Principal principal = doc.getCoreSession().getPrincipal();
        String repoName = doc.getRepositoryName();
        SynchronizationRoots syncRoots = nuxeoDriveManager.getSynchronizationRoots(
                principal).get(repoName);
        if (!includeDeleted && !syncRoots.refs.contains(doc.getRef())) {
            return null;
        }
        if (!doc.isFolder()) {
            throw new IllegalArgumentException(
                    String.format(
                            "Doc %s is a synchronization root but is not Folderish, please check"
                                    + " the consitency of the contributions to the following extension point:"
                                    + " <extension target=\"org.nuxeo.drive.service.FileSystemItemAdapterService\""
                                    + " point=\"fileSystemItemFactory\">.",
                            doc.getPathAsString()));
        }
        return new DefaultSyncRootFolderItem(name, parentId, doc);
    }

    protected FileSystemItemAdapterService getFileSystemItemAdapterService() {
        return Framework.getLocalService(FileSystemItemAdapterService.class);
    }

}
