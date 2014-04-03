import numpy
import json


def build_graph(imdata):
    """
    Takes a 2D numpy matrix containing grayscale bitmap image data and produces
    a graph of boundaries between areas of different pixel values.
    """
    graph = {}  # (x,y): [<neighboring nodes>]

    # traverse each pixel and compare it with its preceding neighbors (in both
    # dimensions), and add extracted edges to the graph.
    for (x, y), value in numpy.ndenumerate(imdata):
        if y and value != imdata[x][y-1]:
            node1 = (y, x)
            node2 = (y, x+1)
            if not node1 in graph:
                graph[node1] = []
            graph[node1].append(node2)
            if not node2 in graph:
                graph[node2] = []
            graph[node2].append(node1)

        if x and value != imdata[x-1][y]:
            node1 = (y, x)
            node2 = (y+1, x)
            if not node1 in graph:
                graph[node1] = []
            graph[node1].append(node2)
            if not node2 in graph:
                graph[node2] = []
            graph[node2].append(node1)

    return graph


def build_paths(graph):
    """
    Takes the graph produced by the build_graph function and extracts a list
    of paths.
    """
    paths = []  # [(x1,y1),(x2,y2),...]

    # we can get away with only caring about nodes with two edges
    simplenodes = filter(lambda x: len(graph[x]) == 2, graph.keys())

    while len(simplenodes):
        next_node = simplenodes.pop()
        new_path = [graph[next_node][0], next_node, graph[next_node][1]]

        # complete path from the end
        while True:
            next_node = new_path[-1]
            if next_node in simplenodes:
                simplenodes.remove(next_node)
                if not graph[next_node][0] in new_path:
                    new_path.append(graph[next_node][0])
                elif not graph[next_node][1] in new_path:
                    new_path.append(graph[next_node][1])
                else:
                    # this should mean the path has circled back around so
                    # we'll explicitly link the ends
                    new_path.append(new_path[0])
                    break
            else:
                break  # this should mean that path has reached a supernode

        # complete path from the start
        while True:
            next_node = new_path[0]
            if next_node in simplenodes:
                simplenodes.remove(next_node)
                if not graph[next_node][0] in new_path:
                    new_path.insert(0, graph[next_node][0])
                elif not graph[next_node][1] in new_path:
                    new_path.insert(0, graph[next_node][1])
                else:
                    break  # this should mean the path has circled back around
            else:
                # this should mean that path has reached a supernode or has
                # already been closed
                break

        paths.append(new_path)

    return paths


def filter_paths(paths, min_length=0, max_paths=0):
    """
    Filters the list of paths, removing paths according to the given criteria.
    """
    if min_length:
        if min_length:
            def keeplongest(min_length):
                def function(array):
                    return len(array) > min_length
                return function
            paths = filter(keeplongest(min_length), paths)

    if max_paths:
        if max_paths:
            paths = sorted(paths, key=len, reverse=True)[:max_paths]

    return paths


def paths2svg(paths, shape, out_file, scale=1, show_nodes=False):
    """
    Write an svg file to preview the paths.
    """
    with open(out_file, 'w') as f:
        f.write("<?xml version=\"1.0\" standalone=\"no\"?>")
        shape = (shape[0]*scale, shape[1]*scale)
        f.write(("<svg width=\"%dpx\" height=\"%dpx\" version=\"1.1\" " +
                 "xmlns=\"http://www.w3.org/2000/svg\">") % shape)

        # draw a black line for each edge
        for path in paths:
            f.write("<path d=\"M%d %d" % (path[0][0]*scale, path[0][1]*scale))
            for node in path[1:]:
                f.write(" L%s %s" % ((node[0]*scale), (node[1]*scale)))
            f.write("\" stroke-width=\"1\" stroke=\"#000\" fill=\"none\"/>")

        # draw a red circle for each node if `show_nodes`
        if show_nodes:
            for path in paths:
                for node in path:
                    params = (node[0]*scale, node[1]*scale, scale)
                    f.write(("<circle cx=\"%d\" cy=\"%d\" r=\"%d\" " +
                             "stroke=\"none\" fill=\"red\" />") % params)
        f.write("</svg>")



def paths2json(paths, out_file):
    """
    Export paths as a JSON file.
    """
    with open(out_file, 'w') as f:
        f.write(json.dumps({
            'number_of_paths': len(paths),
            'number_of_nodes': sum([len(path) for path in paths]),
            'paths': paths
        }))
