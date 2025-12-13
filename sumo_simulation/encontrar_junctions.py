import xml.etree.ElementTree as ET

def list_junction_ids(net_file):
    tree = ET.parse(net_file)
    root = tree.getroot()

    junction_ids = []

    for junction in root.findall("junction"):
        junction_id = junction.get("id")

        # Omitir junctions internos de SUMO
        if junction_id.startswith(":"):
            continue

        junction_ids.append(junction_id)

    return junction_ids


if __name__ == "__main__":
    net_file = "map.net.xml"  # Cambia la ruta si es necesario
    junctions = list_junction_ids(net_file)

    print("Junctions disponibles:")
    for j in junctions:
        print(j)
