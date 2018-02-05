'''
S. Dhanya Abhirami
Follow this link for detailed tutorial: 
https://hackernoon.com/learn-blockchains-by-building-one-117428612f46
'''
# For hashing block
import hashlib
import json
# For timestamp
from time import time
# For parsing url of other nodes in the network
from urllib.parse import urlparse
# For giving requests (used in consensus algorithm)
import requests

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        # Create genesis block
        self.create_new_block(previous_hash=1, proof=100)
        # Maintain a register of all the nodes in the network, set is used to keep it idempotent
        self.nodes = set()
    
    def create_new_block(self, proof, previous_hash=None):
        # Creates a new Block as a dictionary of its details
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]), # previous hash is optional
        }
        # Reset the current list of transactions
        self.current_transactions = []
        # Add block to the chain
        self.chain.append(block)
        return block

    # Add a new node to the list of nodes
    def register_node(self, address):
        parsed_url = urlparse(address)
        # netloc gives hostname https://pymotw.com/2/urlparse/
        self.nodes.add(parsed_url.netloc)

    def new_transaction(self,sender,recipient,amount):
	# Create a dictionary of the transaction details
        trans_details={'sender':sender,'recipient':recipient,'amount':amount}
        # Adds a new transaction to the list of transactions
        self.current_transactions.append(trans_details) 
        # Return index of the block holding this transaction
        return self.chain[-1]['index'] + 1   
    
    @staticmethod
    def hash(block):
        # Hashes a Block
        # Sort the dictionary to get consistent hashes
        # dumps takes an object and produces a string
        block_string = json.dumps(block, sort_keys=True).encode() ### Why encode when you are hashing???
        return hashlib.sha256(block_string).hexdigest()
    
    def proof_of_work(self,last_proof):
        # Simple Proof of Work Algorithm:
        # - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
        # - p is the previous proof, and p' is the new proof

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof
		
    @staticmethod
    def valid_proof(last_proof, proof):
        # Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        # Learn more about f-strings at https://cito.github.io/blog/f-strings/
        guess = (str(last_proof)+str(proof)).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    # Determine if a given blockchain is valid
    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(str(last_block))
            print(str(block))
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    # Consensus Algorithm-resolves conflicts by replacing our chain with the longest one in the network.    
    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get("http://"+str(node)+"/chain")

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

# A universally unique identifier (UUID) is a 128-bit number used to identify information in computer systems.
# Read more about uuid https://docs.python.org/2/library/uuid.html
from uuid import uuid4

# If you are new to Flask go to http://pythonhow.com/how-a-flask-app-works/
from flask import Flask,jsonify,request
# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.chain[-1]
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof ;)
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge(Create) the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.create_new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response),200
	# https://stackoverflow.com/questions/7907596/json-dumps-vs-flask-jsonify

# POST because we will be sending data   
@app.route('/transactions/new', methods=['POST']) 
def new_transaction():
	return "We'll add a new transaction"

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200 # Return full blockchain (200 OK)

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000,debug=True)