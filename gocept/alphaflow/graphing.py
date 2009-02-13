# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import os
import tempfile

import logging

import zope.component
import zope.interface

import Products.AlphaFlow.interfaces
import Products.AlphaFlow.utils

try:
    import pydot
except ImportError:
    Products.AlphaFlow.utils.logger.log(
        logging.WARN, "pydot is not installed. The visual editor will "
        "not be fully functional.")
    pydot = None

format_contenttype = {}
format_contenttype['cmapx'] = 'text/xml'
format_contenttype['png'] = 'image/png'

# These are some helper methods to simplify operating on a DOT graph.

def get_group_color(group):
    return '#e29191'


def group_node_name(group):
    return 'afeditorgroup_%s' % group


class Graph(pydot.Dot):

    def outgoing_neighbors(self, node):
        """Returns a set of all neighbors that this node has outgoing
        edges to.
        """
        neighbors = set()
        for candidate in self.get_node_list():
            if self.get_edge(node.name, candidate.name) is not None:
                neighbors.add(candidate)
        return neighbors

    def _filter_edges(self, condition, subset):
        """Returns a list of edges that match the given condition for a given
        subset of the graph's nodes.
        """
        if subset is None:
            subset = self.get_node_list()

        # We only need the IDs to compute with.
        inner_nodes = set([node.get_name() for node in subset])

        result_edges = set()

        for edge in self.get_edge_list():
            if condition(edge, inner_nodes):
                result_edges.add(edge)
        return result_edges

    def out_edges_iter(self, subset=None):
        def condition(edge, nodes):
            return (edge.get_source() in nodes and
                   edge.get_destination() not in nodes)
        return self._filter_edges(condition, subset)

    def in_edges_iter(self, subset=None):
        def condition(edge, nodes):
            return (edge.get_source() not in nodes and
                    edge.get_destination() in nodes)
        return self._filter_edges(condition, subset)

    def delete_edge(self, edge):
        # XXX The edge_src and edge_dst lists are not updated!
        self.edge_list.remove(edge)
        careful_remove(edge, self.sorted_graph_elements)

    def delete_node(self, node):
        "Removes a node and all adjacent edges."
        node_name = node.get_name()
        for edge in list(self.get_edge_list()):
            if (edge.get_source() == node_name or
                edge.get_destination() == node_name):
                self.delete_edge(edge)
        careful_remove(node, self.node_list)
        careful_remove(node, self.sorted_graph_elements)
        careful_remove(node.get_name(), self.edge_src_list)
        careful_remove(node.get_name(), self.edge_dst_list)



def careful_remove(item, data):
    # A workaround for broken pydot data structures.
    for i, candidate in enumerate(list(data)):
        if candidate is item:
            del data[i]


class WorkflowGraph(object):

    zope.component.adapts(Products.AlphaFlow.interfaces.IProcessVersion)
    zope.interface.implements(Products.AlphaFlow.interfaces.IWorkflowGraph)

    zoom = '2'
    highlight = None
    expand_groups = []

    def __init__(self, process):
        self.process = process 

    def render(self, format):
        dot = self._generate_dot()
        output = self._generate_output(dot, format)

        return output

    def _generate_dot(self):
        "Returns a graph definition in DOT format."
        if pydot is None:
            raise RuntimeError("pydot not installed")
        graph = Graph(type='graph', simplify=True, graph_name="G",
                      size='%s,%s!' % (self.zoom, self.zoom))
        # We need to maintain our own `seen` set because the graph will
        # implicitly create nodes as soon as we create edges that use them.
        seen = set()
        queue = []
        queue.extend(self.process.startActivity)

        # Establish all nodes
        while queue:
            node = queue.pop(0)
            seen.add(node)

            existing_node = graph.get_node(node)
            if not existing_node:
                graph.add_node(pydot.Node(node))

            if node not in self.process.keys():
                continue

            for child in self.process[node].graphGetPossibleChildren():
                child_id = child['id']
                edge = pydot.Edge(node, child_id)
                edge.qualifier = child.get('qualifier')
                graph.add_edge(edge)

                if child_id not in seen:
                    queue.append(child_id)

        # Post-process the graph to add more information and details

        # Set up labels for nodes
        for node in graph.get_node_list():
            node_name = node.get_name()
            if node_name not in self.process.keys():
                continue
            title = self.process[node_name].title
            if title:
                node.set('label', title.encode('utf8'))

        # Process qualifier==`parent`
        for edge in graph.get_edge_list():
            if not edge.qualifier == 'parent':
                continue
            edge.color = 'khaki'
            destination_node = graph.get_node(edge.get_destination())
            parents = graph.in_edges_iter([destination_node])
            for candidate in parents:
                if candidate.qualifier == 'parent':
                    continue
                candidate.dir = 'both'
                candidate.color = 'black:khaki'

        # Set up shapes
        # XXX Very big XXX
        for node in graph.get_node_list():
            if (node.name in self.process.keys() and
                self.process[node.name].activity_type in ['switch', 'ntask',
                                                          'decision']):
                node.set('shape', 'ellipse')
            else:
                node.set('shape', 'box')

        # Setup parentOf markers

        # Setup start node
        start_node = pydot.Node('__init__')
        start_node.shape = 'point'
        graph.add_node(start_node)

        # Mark start activities
        for node in graph.get_node_list():
            if node.name in self.process.startActivity:
                graph.add_edge(pydot.Edge('__init__', node.name))

        # Highlight selected node
        for node in graph.get_node_list():
            if node.name == self.highlight:
                node.style = 'bold'

        group_merges = {}
        # Merge groups
        for node in graph.get_node_list():
            if not node.name in self.process.keys():
                continue
            group = getattr(self.process[node.name], 'group', None)
            if group is None:
                continue

            # Don't create nodes for expanded groups
            if group in self.expand_groups:
                continue
            members = group_merges.setdefault(group, set())
            members.add(node)

        # Create a node for each group
        for group in group_merges:
            node = pydot.Node(group_node_name(group))
            graph.add_node(node)
            node.set('fillcolor', get_group_color(group))
            node.set('shape', 'egg')
            node.set('style', 'filled')
            node.set('label', group)
            node.set('URL', 'expand-group://%s' % group)

        for group in group_merges:
            members = group_merges[group]
            # Add incoming and outgoing connections for the groups
            for out_edge in graph.out_edges_iter(members):
                graph.add_edge(pydot.Edge(group_node_name(group),
                                          out_edge.get_destination()))
            for in_edge in graph.in_edges_iter(members):
                graph.add_edge(pydot.Edge(in_edge.get_source(), group_node_name(group)))
            # Remove all group member nodes
            for member in members:
                graph.delete_node(member)

        # Setup URLs for editing the activities
        for node in graph.get_node_list():
            if node.name in self.process.keys():
                node.set('URL', 'activity://%s' % node.name)

        return graph

    def _generate_output(self, dot, format):
        """Processes a dot graph to an output format.

        Returns the output from graphviz.

        """
        return dot.create(format=format)
