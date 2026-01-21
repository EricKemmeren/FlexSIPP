from matplotlib.axis import Axis


class Results:
    def __init__(self, s:str):
        #s is a string with the text output of a repeat search this parses it into the compount atf, and the individual augmentded SIPP plans for each segment
        self.metadata= {}
        self.unique_paths = {}
        self.unique_path_eatfs = {}
        s = s.splitlines() # avoid empty element in list
        self.parse_list_of_outputs(s)

    def parse_list_of_outputs(self, s, offset=0):
        # s is the output split on newline characters
        i = 0
        while "Nodes generated" not in s[i]:
            i += 1
        lns = s[i].split(" ")
        self.metadata["Nodes generated"] = lns[2]
        self.metadata["Nodes decreased"] = lns[5]
        self.metadata["Nodes expanded"] = lns[8]
        i+=1
        self.catf = s[i].strip(", ").split(", ") # avoid empty element in list
        self.catf = [tuple([str(round(float(y) - offset, 2)) for y in (x.strip("'").strip("<").strip(">").split(","))]) for x in self.catf]
        i += 1
        paths = []
        eatfs = []
        while i < len(s) and "time: " not in s[i]:
            paths.append([])
            while "time: " not in s[i] and (s[i][0] != "<") and (s[i][-1] != ">"):
                # s[i]: "node_name node_safe_interval node_id"
                paths[-1].append(s[i].split(" ")[0])
                i += 1
            atf = s[i]
            atf = atf.strip("<").strip(">").split(",")
            gammas = [gamma[1:-1].split(": ") for gamma in atf[-1][1:-1].split("; ")[0:-1]]
            atf[-1] = gammas
            for j in range(len(atf) - 2):
                atf[j] = str(round(float(atf[j]) - offset, 2))
            atf = tuple(atf)
            eatfs.append(atf)
            i += 1

        search_time = s[i].split(" ")
        self.metadata["Search time"] = search_time[-2]

        if [] in paths:
            paths.remove([]) # because the last path added stays empty

        for (i,p) in enumerate(paths):
            path_string = ";".join(p)
            if path_string in self.unique_paths:
                self.unique_paths[path_string] += 1
                if eatfs[i] not in self.unique_path_eatfs[path_string]:
                    self.unique_path_eatfs[path_string].append(eatfs[i])
            else:
                self.unique_paths[path_string] = 1
                self.unique_path_eatfs[path_string] = [eatfs[i]]

    linestyles = [
        (0, (5, 10)),
        (5, (5, 10)),
        (10, (5, 10)),
        (0, (5, 0))
    ]

    def plot(self, ax: Axis, **kwargs):
        color = kwargs.get('color', None)
        label = kwargs.get('label', None)
        linestyle = Results.linestyles[kwargs.get('linestyle', 0)]

        y_offset = kwargs.get('y_offset', 0)

        line = None
        for (x0, x1, y0, y1) in self.catf:
            if x0 == "-inf" and x1 != "inf" and y1 != "inf":
                ax.hlines(float(y1) + y_offset, 0, float(x1), colors=color, linestyle=linestyle)
            line, = ax.plot([float(x0), float(x1)], [float(y0) + y_offset, float(y1) + y_offset], color=color,
                            linestyle=linestyle)
        line.set_label(label) if line is not None else None

def test():
    Results(
        "\n".join(['Arrival time: 130.667',
                   'Nodes generated: 10 Nodes decreased: 0 Nodes expanded: 8',
                   '<-inf,20,130.667,130.667>, '
                   '<20,50,130.667,160.667>, '
                   '<50,inf,inf,inf>, '
                   '',
                   't-EHB <0,50> ns:1',
                   's-123BL <0,150> ns:2',
                   's-125BR <93,160> ns:2',
                   's-131B <88,170> ns:2',
                   't-401B <115,2000> ns:1',
                   't-401A <115,2000> ns:2',
                   '<-inf,20,50,110.667>',
                   't-EHB <0,50> ns:1',
                   's-123BL <0,150> ns:2',
                   's-125BR <93,160> ns:2',
                   's-131B <88,170> ns:2',
                   't-401B <115,2000> ns:1',
                   't-401A <115,2000> ns:2',
                   '<-inf,20,50,110.667>',
                   '<0,0,inf,inf>',
                   'Search time: 1141791 nanoseconds',
                   'Total (n=100) Lookup time: 10917 nanoseconds'])
)
        # run $ python3 -c 'from parseRePEAT import *; test()'
