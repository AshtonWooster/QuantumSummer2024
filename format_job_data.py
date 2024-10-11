from glob import glob
import json
import csv
from qiskit_ibm_runtime import QiskitRuntimeService

# Configuration values
user_token = ''
backend_machine = 'ibm_sherbrooke'
jobs_path = 'ran_jobs/*.json'
expected_output = '1101'

service = QiskitRuntimeService(
    channel='ibm_quantum',
    instance='ibm-q/open/main',
    token=user_token
)

# Gets the connections from the backend, shouldn't change from Osaka to Sherbrooke
backend = service.backend(backend_machine)
gates = backend.properties().gates
connections = []
for gate in gates:
    if gate.gate == 'ecr':
        connections.append(gate)

# Making a list of the jobs ran with the data needed for the model
def make_jobs_list():
    jobs_data = []
    for file_name in glob(jobs_path):
        with open(file_name, 'r') as file:
            mapping = json.load(file)
            print("\tGetting Data for " + str(mapping['id']))

            # Only use the anchor circuit
            physical_qubits = []
            for logical_qubit in mapping['mapping']:
                if int(logical_qubit) < 5:
                    physical_qubits.append(mapping['mapping'][logical_qubit])
            mapping['physical_qubits'] = physical_qubits

            # Grabs the job properties given the id in the mapping json
            job = service.job(job_id=mapping['id'])
            properties = job.properties()

            # Gets the accuracy
            if job.status() != 'DONE':
                continue
            databin = job.result()[0].data.__dict__
            accuracy = 0
            if 'c_0' in databin:
                accuracy = databin['c_0'].get_counts()[expected_output] / 8192
            else:
                accuracy = databin['c'].get_counts()[expected_output] / 8192
            mapping['accuracy'] = accuracy

            # Gets the qubit qualities from the job.properties()
            qubit_qualities = {}
            for qubit_number in physical_qubits:
                qubit_qualities[str(qubit_number)] = properties.readout_error(qubit_number)
            mapping['qubit_qualities'] = qubit_qualities

            # Gets the gate qualities
            gate_qualities = {}
            for connection in connections:
                qubits = connection.qubits
                if qubits[0] in physical_qubits and qubits[1] in physical_qubits:
                    gate_name = connection.name
                    gate_qualities[gate_name] = connection.parameters[0].value
            mapping['gate_qualities'] = gate_qualities

            jobs_data.append(mapping)
    return jobs_data

# Writes the data to a CSV file for the random forest model
def write_data(jobs_data):
    with open('jobs_data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['job_id', 'num_circuits', 'padding', 'qubit_0', 'qubit_1', 'qubit_2', 'qubit_3', 'qubit_4',
                         'qubit_0_quality', 'qubit_1_quality', 'qubit_2_quality', 'qubit_3_quality', 'qubit_4_quality',
                         'gate_0', 'gate_1', 'gate_2', 'gate_3', 'gate_0_quality', 'gate_1_quality', 'gate_2_quality', 'gate_3_quality', 'accuracy'])
        
        for job_data in jobs_data:
            job_id = job_data['id']
            num_circuits = job_data['register_count']
            padding = job_data['padding']
            qubit_0, qubit_1, qubit_2, qubit_3, qubit_4 = job_data['physical_qubits']
            qubit_0_quality, qubit_1_quality, qubit_2_quality, qubit_3_quality, qubit_4_quality = job_data['qubit_qualities'].values()
            gate_0, gate_1, gate_2, gate_3 = job_data['gate_qualities'].keys()
            gate_0_quality, gate_1_quality, gate_2_quality, gate_3_quality = job_data['gate_qualities'].values()
            accuracy = job_data['accuracy']

            writer.writerow([job_id, num_circuits, padding, qubit_0, qubit_1, qubit_2, qubit_3, qubit_4,
                            qubit_0_quality, qubit_1_quality, qubit_2_quality, qubit_3_quality, qubit_4_quality,
                            gate_0, gate_1, gate_2, gate_3, gate_0_quality, gate_1_quality, gate_2_quality, gate_3_quality, accuracy])

print("Making job data list...\n")
jobs_data = make_jobs_list()

print("\nCompleted, writing data to jobs_data.csv")
write_data(jobs_data)
