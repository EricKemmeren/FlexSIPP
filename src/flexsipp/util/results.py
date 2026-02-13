from matplotlib.axis import Axis
import pickle

class Results:
    def __init__(self):
        self.metadata= {}
        self.unique_paths = {}
        self.unique_path_eatfs = {}

    @classmethod
    def parse_list_of_outputs(cls, s, offset=0):
        #s is a string with the text output of a repeat search this parses it into the compount atf, and the individual augmentded SIPP plans for each segment
        self = cls()
        s = s.splitlines() # avoid empty element in list
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
        
        return self

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

    def save(self, file):
        with open(file, "wb") as outp:
            pickle.dump(self, outp, pickle.HIGHEST_PROTOCOL)

    def compare_paths(self, f, original_path:list[str]):
        paths:list[str] = [key.split(";") for key in self.unique_paths.keys()]
        def split_list_on_gaps(path: list[int]) -> list[list[int]]:
            if not path:
                return [path]
            result = []
            result.append([path[0]])
            for p in path[1:]:
                if p - 1 == result[-1][-1]:
                    result[-1].append(p)
                else:
                    result.append([p])
            return result
        
        for path in paths:
            # Find differences in the paths between original and new
            differences = list(set(path) - set(original_path))
            diff_index = [path.index(i) for i in differences]
            diff_index.sort()

            largest_beta = max([b for z,a,b,d,g in self.unique_path_eatfs[";".join(path)]])

            f.write(f"Path differences when departing before {largest_beta}\n")
            for diffs in split_list_on_gaps(diff_index):
                differences = [path[i] for i in diffs]
                f.write(", ".join(differences))
                f.write("\n")
            f.write("\n")


if __name__ == "__main__":
    with open(r"C:\Users\eoss3\Documents\FlexSIPP\FlexSIPP\data\friso\demo_backup\update-00\results.pkl", "rb") as f:
        data = pickle.load(f)

    with open(r"C:\Users\eoss3\Documents\FlexSIPP\FlexSIPP\data\friso\demo_backup\update-00\results2.txt", "w") as f:
        data.compare_paths(f, ['LPE-1284', 'LPE-1264', 'BTL_LPE-1236', 'BTL-1194', 'BTL-1124', 'BTL_TB-1542', 'BTL_TB-1536', 'BTL_TB-1532', 'BTL_TB-1528', 'BTL_TB-1522', 'BTL_TB-528', 'BTL_TB-524', 'BTL_TB-518', 'BTL_TB-512', 'BTL_TB-506', 'TB-168', 'TB-892', 'TB-130', 'TB-116', 'TBU-96', 'TBU-72', 'BD_TBU-874', 'BD_TBU-870', 'BD_TBU-866', 'BD_TBU-862', 'BD_TBU-858', 'BD_TBU-852', 'BD_TBU-846', 'BD_TBU-836', 'BD_TBU-830', 'BD_TBU-826', 'BD_TBU-822', 'BD_TBU-818', 'BD_TBU-812', 'BD-1150', 'BD-1136', 'BD-1080', 'BD-1044', 'BD-1028', 'BD_ZHA-703', 'BD_ZHA-709', 'BD_ZHA-715', 'ZHA-526', 'ZHA-508', 'ZHA-2376', 'RTDBD-2356', 'RTDBD-2346', 'RTDBD-2336', 'RTDBD-2326', 'RTDBD-2316', 'RTDBD-2306', 'RTDBD-2296', 'RTDBD-2286', 'RTDBD-2276', 'RTDBD-2266', 'RTDBD-2256', 'KFHAZ_RTDBD-710'])