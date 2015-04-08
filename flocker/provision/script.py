# Copyright Hybrid Logic Ltd.  See LICENSE file for details.

"""
The command-line ``flocker-provision`` tool.
"""
from sys import stdout
import yaml

from twisted.internet.defer import succeed, fail
from twisted.python.usage import Options

from zope.interface import implementer
# TODO separate FEEDBACK_CLI_TEXT to somewhere shared from flocker.cli.script
from flocker.cli.script import FEEDBACK_CLI_TEXT

from ..common.script import (flocker_standard_options, ICommandLineScript,
                             FlockerScriptRunner)

from flocker.provision import CLOUD_PROVIDERS, PackageSource
from flocker.provision._install import (
    configure_cluster,
)


class CreateOptions(Options):
    # TODO longdesc and synopsis
    optParameters = [
        ['driver', 'd', 'rackspace', 'choose cloud provider'],
        ['username', None, None, 'Rackspace account username'],
        ['api-key', None, None, 'Rackspace API key'],
        # TODO default region? Does a user care? If so print this
        ['region', None, None, 'Rackspace region'],
        ['ssh-key-name', None, None, 'Name of Rackspace SSH key.'],
        ['num-agent-nodes', 'n', 3, 'how many nodes to create'],
    ]

    def postOptions(self):
        self.provisioner = CLOUD_PROVIDERS[self['driver']](
            username=self['username'],
            key=self['api-key'],
            region=self['region'],
            keyname=self['ssh-key-name'],
        )


@flocker_standard_options
class ProvisionOptions(Options):
    """
    Command line options for ``flocker-provision``.
    """
    longdesc = """flocker-provision...

    """

    # TODO Fix this
    synopsis = ("Usage: flocker-provision [OPTIONS] "
                "DEPLOYMENT_CONFIGURATION_PATH APPLICATION_CONFIGURATION_PATH"
                "{feedback}").format(feedback=FEEDBACK_CLI_TEXT)

    # TODO check other commands for period
    subCommands = [['create', None, CreateOptions, "Create a Flocker cluster"]]

    def parseArgs(self):
        pass


def create(reactor, provisioner, num_agent_nodes, output):
    # This uses the reactor because we will start using conch
    # and node.provision will return a deferred, as will configure_cluster.
    nodes = []
    for index in range(num_agent_nodes) + 1):
        name = "flocker-provisioning-script-%d" % (index,)
        try:
            print "Creating node %d: %s" % (index, name)
            node = provisioner.create_node(
                name=name,
                distribution='centos-7',
            )
        except:
            print "Error creating node %d: %s" % (index, name)
            print "It may have leaked into the cloud."
            # TODO give the IP address of the nodes to a user,
            # or perhaps destroy nodes
            # or perhaps say "you may want to destroy nodes called flocker-XXX"
            raise

        nodes.append(node)

        node.provision(package_source=PackageSource(),
                       variants=set())

    control_node = nodes[0].address
    agent_nodes = [agent.address for agent in nodes[1:]]
    configure_cluster(control_node=control_node, agent_nodes=agent_nodes)
    print yaml.safe_dump({
        'control_node': control_node,
        'agent_nodes': agent_nodes,
    })
    return succeed(None)


@implementer(ICommandLineScript)
class ProvisionScript(object):
    """
    A command-line script to interact with a cluster via the API.
    """
    def main(self, reactor, options):
        """
        See :py:meth:`ICommandLineScript.main` for parameter documentation.

        :return: A ``Deferred`` which fires when the deployment is complete or
                 has encountered an error.
        """
        if options.subCommand == 'create':
            return create(
                reactor,
                provisioner=options.provisioner,
                num_agent_nodes=options['num-agent-nodes'],
                output=stdout)
        else:
            return fail(ValueError("Unknown subcommand %s.", (options.subCommand)))


def flocker_provision_main():
    # There is nothing to log at the moment, so logging is disabled.
    return FlockerScriptRunner(
        script=ProvisionScript(),
        options=ProvisionOptions(),
        logging=False,
    ).main()
