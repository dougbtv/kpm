import logging
import kpm.semver as semver
import kpm.models as models


logger = logging.getLogger(__name__)


def _get_package(package, version_query='latest'):
    """
      Fetch the package data from the datastore
      and instantiate a :obj:`kpm.models.package_base.PackageModelBase`

    Args:
      package (:obj:`str`): package name in the format "namespace/name" or "domain.com/name"
      version_query (:obj:`str`): a version query, eg: ">=1.5,<2.0"

    Returns:
      :obj:`kpm.kub_jsonnet.KubJsonnet`: :obj:`kpm.models.package_base.PackageModelBase`

    See Also:
       * :obj:`kpm.api.models.package_base.PackageModelBase`
       * :obj:`kpm.api.models.etcd.package.Package`

    Raises:
      :obj:`kpm.exception.PackageNotFound`: package not found
      :obj:`kpm.exception.InvalidVersion`: version-query malformated
      :obj:`kpm.exception.PackageVersionNotFound`: version-query didn't match any release

    """
    # if version is None; Find latest version
    p = models.Package.get(package, version_query)
    return p


def pull(package, version='latest'):
    """
    Retrives the package blob from the datastore

    Args:
      package (:obj:`str`): package name in the format "namespace/name" or "domain.com/name"
      version_query (:obj:`str`): a version query, eg: ">=1.5,<2.0"

    Returns:
      :obj:`dict`: package data
        * package: package name
        * version: version that matched the version query
        * filename: suggested filename to create the tarball
        * blob: a `tar.gz` encoded in base64.

    Example:
      >>> kpm.api.impl.registry.pull("coreos/etcd", version=">=3")
        {
         'blob': 'H4sICHDFvlcC/3RpdF9yb2NrZXRjaGF0XzEuMTAuMGt1Yi50YXIA7ZdRb5swEM',
         'filename': u'coreos_etcd_3.0.1.tar.gz',
         'package': 'coreos_etcd',
         'version': u'3.0.1'
        }

    Raises:
      :obj:`kpm.exception.PackageNotFound`: package not found
      :obj:`kpm.exception.InvalidVersion`: version-query malformated
      :obj:`kpm.exception.PackageVersionNotFound`: version-query didn't match any release

    See Also:
       * :obj:`kpm.api.registry.pull`

    """

    packagemodel = _get_package(package, version)
    resp = {"package": package,
            "blob": packagemodel.blob,
            "version": packagemodel.version,
            "filename": "%s_%s.tar.gz" % (packagemodel.package.replace("/", "_"), packagemodel.version)}
    return resp


def push(package, version, blob, force=False):
    """
    Push a new package release in the the datastore

    Args:
      package (:obj:`str`): package name in the format "namespace/name" or "domain.com/name"
      version (:obj:`str`): the 'exact' package version (this is not a version_query)
      blob (:obj:`str`): the package directory in `tar.gz` and encoded in base64
      force (:obj:`boolean`): if the package exists already, overwrite it

    Returns:
      :obj:`dict`: push status

    Example:
      >>> kpm.api.impl.registry.push("coreos/etcd", "3.0.1",
            "H4sICHDFvlcC/3RpdF9yb2NrZXRjaGF0XzEuMTAuMGt1Yi50YXIA7ZdRb5swEM")
        {
         'status': u'ok'
        }

    Raises:
      PackageAlreadyExists: if package already exists and `force` is False

    See Also:
       * :obj:`kpm.api.registry.push`

    """
    p = models.Package(package, version, blob)
    p.save(force=force)
    return {"status": "ok"}


def list_packages(organization=None):
    """
    List all packages, filters can be applied
    Must have at least a release to be visible

    Todos:
       - sort_by: name, created_at, downloads, number of stars
       - filter_by: users

    Args:
      organization (:obj:`str`): returns packages from the `organization` only

    Returns:
      :obj:`list of dict`: list packages
        * name: package name
        * available_versions (list of str):  All releases
        * created_at (datetime, optional): package creation date
        * downloads (int, optional): number of downloads
        * version: release name

    Example:
      >>> kpm.api.impl.registry.list_packages()
      [
       {
        'available_versions': ['0.1.0'],
        'name': u'quentinm/rados-gateway',
        'version': '0.1.0',
        'created_at": "2016-04-22T11:58:34.103Z",
        'downloads': 41
       },
       {
        'available_versions': ['0.1.0'],
        'name': u'quentinm/nova',
        'version': '0.1.0'
       },
      ]

    See Also:
       * :obj:`kpm.api.registry.list_packages`
    """
    resp = models.Package.all(organization)
    return resp


def show_package(package, version="latest", pullmode=False):
    """
    Returns package details

    Args:
      package (:obj:`str`): package name in the format "namespace/name" or "domain.com/name"
      version (:obj:`str`): the 'exact' package version (this is not a version_query)
      pullmode (:obj:`boolean`): include the package blob in the response

    Returns:
      :obj:`dict`: package data
        * version (str)
        * name (str)
        * created_at (str)
        * channels (list)
        * available_versions (list)
        * dependencies (list)
        * variables (dict)
        * manifest (str)

    Example:
      >>> kpm.api.impl.registry.show_package("ns/mypackage")
      {
      "version": "3.2.0-rc",
      "name": "ns/mypackage",
      "created_at": "2016-08-25T10:16:16.366758",
      "channels": [
       {
        "current": "3.1.0",
        "channel": "stable",
        "releases": [
          "3.1.0"
          "3.0.1"
        ]
       },
      ],
      "available_versions": [
        "3.2.0-rc"
        "3.1.0",
        "3.0.1"
      ],
      "dependencies": [
        "ns/dep1",
        "ns/dep2",
        "ns/dep3"
       ],
       "variables": {
         "replicas": 1,
         "image": "ns/mypackage:latest",
         "namespace": "default",
         "cluster": "cluster.local",
         "mail_url": "smtp://"
       },
      "manifest": "---...."
       }

    Raises:
      :obj:`kpm.exception.PackageNotFound`: package not found
      :obj:`kpm.exception.InvalidVersion`: version-query malformated
      :obj:`kpm.exception.PackageVersionNotFound`: version-query didn't match any release

    See Also:
       * :obj:`kpm.api.registry.show_package`
    """
    stable = False
    packagemodel = _get_package(package, version)
    manifest = packagemodel.manifest()
    response = {"manifest": packagemodel.packager.manifest,
                "version": packagemodel.version,
                "name":  package,
                "created_at": packagemodel.created_at,
                "variables": manifest.variables,
                "dependencies": manifest.dependencies,
                "channels": models.Channel.all(package).values(),
                "available_versions": [str(x) for x in sorted(semver.versions(packagemodel.versions(), stable),
                                                              reverse=True)]}
    if pullmode:
        response['kub'] = packagemodel.b64blob
    return response


# CHANNELS
def list_channels(package):
    """
    List all channels for a given package

    Args:
      package (:obj:`str`): package name in the format "namespace/name" or "domain.com/name"

    Returns:
      :obj:`list of dict`: list channels:
        * channel (str): channel name
        * current (str): latest/default release associated to the channel
        * releases (list): list channel's releases

    Example:
      >>> kpm.api.impl.registry.list_channels("myns/package")
      [{'channel': u'stable', 'current': '1.10.2', 'releases': [u'1.10.2']},
       {'channel': u'dev', 'current': 2.0.0-beta, 'releases': [1.10.2, 2.0.0-beta]}]

    See Also:
       * :obj:`kpm.api.registry.list_channels`
    """
    channels = models.Channel.all(package).values()
    return channels


def show_channel(package, name):
    """
    Show channel info
    Args:
      package (:obj:`str`): package name in the format "namespace/name" or "domain.com/name"
      name (:obj:`str`): channel name to inspect

    Returns:
      :obj:`dict`: channel info
        * channel (str): channel name
        * current (str): latest/default release associated to the channel
        * releases (list): list channel's releases

    Example:
      >>> kpm.api.impl.registry.list_channels("tit/rocketchat", 'dev')
      {'channel': u'dev', 'current': '2.0.0-beta', 'releases': [u'1.10.2']}

    Raises:
      :obj:`kpm.api.exception.ChannelNotFound`: channel not found

    See Also:
       * :obj:`kpm.api.registry.show_channel`
    """
    c = models.Channel(name, package)
    return c.to_dict()


def add_channel_release(package, name, release):
    """
    Add a package-release to a channel
    Args:
      package (:obj:`str`): package name in the format "namespace/name" or "domain.com/name"
      name (:obj:`str`): channel name to inspect
      release (:obj:`str`): package version to add

    Returns:
      :obj:`dict`: channel info
        * channel (str): channel name
        * current (str): latest/default release associated to the channel
        * releases (list): list channel's releases

    Example:
      >>> kpm.api.impl.registry.list_channels("tit/rocketchat", 'dev')
      {'channel': u'dev', 'current': '2.0.0-beta', 'releases': [u'1.10.2']}

    Raises:
      :obj:`kpm.api.exception.ChannelNotFound`: channel not found

    See Also:
       * :obj:`kpm.api.registry.add_channel_release`
    """
    channel = models.Channel(name, package)
    channel.add_release(release)
    return channel.to_dict()


def delete_channel_release(package, name, release):
    """
    Remove a release from a channel

    Args:
      package (:obj:`str`): package name in the format "namespace/name" or "domain.com/name"
      name (:obj:`str`): channel name to inspect
      release (:obj:`str`): package version to add

    Returns:
      :obj:`dict`: channel info
        * channel (str): channel name
        * current (str): latest/default release associated to the channel
        * releases (list): list channel's releases

    Example:
      >>> kpm.api.impl.registry.list_channels("tit/rocketchat", 'dev')
      {'channel': u'dev', 'current': '2.0.0-beta', 'releases': [u'1.10.2']}

    Raises:
      :obj:`kpm.api.exception.ChannelNotFound`: channel not found

    See Also:
       * :obj:`kpm.api.registry.delete_channel_release`
    """
    channel = models.Channel(name, package)
    channel.remove_release(release)
    return channel.to_dict()


def create_channel(package, name):
    channel = models.Channel(name, package)
    channel.save()
    return channel.to_dict()


def delete_channel(package, name):
    channel = models.Channel(name, package)
    channel.delete()
    return {"channel": channel.name, "package": package, "action": 'delete'}


def delete_package(package, version="latest"):
    packagemodel = _get_package(package, version)
    models.Package.delete(packagemodel.package, packagemodel.version)
    return {"status": "delete", "package": packagemodel.package, "version": packagemodel.version}
