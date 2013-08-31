import random
import pprint
import sys

# Each insn is a python dictionary (map) with the following fields:
# 
#   src1 - operand #1 source register id
#   src2 - operand #2 source register id
#   dst - destination register id
# 
# Register id's are just integers.  There are 16 architectural
# registers in this simple ISA, with id's 0 to 15.
# 
# There are two additional fields which you should fill in as you
# schedule instructions according to their dependences.
#
#   consumer_insns - list of insns that consume output of this insn
#   depth - depth of insn in the scheduling tree


PHYS_REG_FREE_LIST = [i for i in range(16)]
LOG_PHYS_MAP = []
ISSUE_QUEUE = []
READY_BITS = []
PHYS_REG_MAP = []
MAX_WIDTH = 0
toremove = []

def gen_insns(n):
    # Unique root insn to make sure our dependencies form a tree.
    insns = [ {'src1':0, 'src2':0, 'dst':0,
               'consumer_insns':[], 'depth':0} ]

    live_regs = set([0]) # start out with only 1 live reg
    for i in range(n):
        insn = {}
        insn['src1'] = random.choice(list(live_regs))
        insn['src2'] = random.choice(list(live_regs))
        insn['dst'] = random.randint(0, 15)
        live_regs.add(insn['dst'])

        # Used for building dependence tree.
        insn['consumer_insns'] = []

        # Used for calculating program latency.
        insn['depth'] = None

        insns.append(insn)
    return insns

def get_preg_from_table(op_reg):

    for i in range(len(LOG_PHYS_MAP)):
        if LOG_PHYS_MAP[i][0] == op_reg:
            return LOG_PHYS_MAP[i][1]

    return -1

def insert_into_map_table(lreg, preg):
    
    global LOG_PHYS_MAP

    for i in range(len(LOG_PHYS_MAP)):
        if LOG_PHYS_MAP[i][0] == lreg:
            LOG_PHYS_MAP[i][1] = preg
            return

    LOG_PHYS_MAP.append([lreg, preg])

    pass

def initialize_preg_map():

    global PHYS_REG_MAP

    for i in range(16):
        PHYS_REG_MAP.append([False, False])

    return

def rename(insn):

    global PHYS_REG_FREE_LIST
    global LOG_PHYS_MAP

    # list of src operands
    src_ops = [insn['src1'], insn['src2']]

    # look up the logical register in the map table and use the register if it is assigned
    for i in range(len(src_ops)):
        # get the physical register from the map
        preg = get_preg_from_table(src_ops[i])
        if(preg != -1):
            src_ops[i] = preg
        else:
            preg = PHYS_REG_FREE_LIST.pop(0)
            insert_into_map_table(src_ops[i], preg)
            src_ops[i] = preg          
    
    # rename the operands
    insn['src1'] = src_ops[0]
    insn['src2'] = src_ops[1]

    # rename the dst reg
    preg = PHYS_REG_FREE_LIST.pop(0)
    insert_into_map_table(insn['dst'], preg)
    insn['dst'] = preg
    
    pass

def build_issue_queue(insns):

    global ISSUE_QUEUE

    initialize_ready_bits()

    age = 0

    for i in insns:
        queue_entry = {'src1': i['src1'], 'src1ready': isready(i['src1']), 'src2': i['src2'], 'src2ready': isready(i['src2']), 'dst': i['dst'], 'age': age, 'insnid': i}
        set_not_ready(i['dst'])
        ISSUE_QUEUE.append(queue_entry)
        age+=1

    return

def initialize_ready_bits():

    for i in range(PHYS_REG_FREE_LIST[0]):
        READY_BITS.append([i, True])

    return

def isready(i):

    for j in range(len(READY_BITS)):
        if(i == READY_BITS[j][0]):
            return READY_BITS[j][1]

    return False

def set_not_ready(i):

    for j in range(len(READY_BITS)):
        if(i == READY_BITS[j][0]):
            READY_BITS[j][1] = False

    return False

def set_ready(i):

    for j in range(len(READY_BITS)):
        if(i == READY_BITS[j][0]):
            READY_BITS[j][1] = True

    return False

def compute_latency(insns):
    tickcount = 0
    initialize_preg_map()
    # build issue queue
    build_issue_queue(insns)
    while (len(ISSUE_QUEUE) > 0):
        select(insns, tickcount)
        tickcount+=1
        wakeup()

    return tickcount

def set_insn_depth(element, insns, tickcount):
    
    element['insnid']['depth'] = tickcount+1

    return

def select(insns, tickcount):

    global MAX_WIDTH
    global toremove

    toremove = []

    for i in range(len(ISSUE_QUEUE)):
        element = ISSUE_QUEUE[i]
        if (element['src1ready'] == True and element['src2ready'] == True):
            set_ready(element['dst'])
            toremove.append(element)
            set_insn_depth(element, insns, tickcount)
            map_preg(element)
    
    for i in range(len(toremove)):
        remove_insn_from_issue_queue(toremove[i])

    if (len(toremove) > MAX_WIDTH):
        MAX_WIDTH = len(toremove)

    return

def map_preg(element):

    global PHYS_REG_MAP

    PHYS_REG_MAP[element['src1']][0] = True
    PHYS_REG_MAP[element['src1']][1] = True
    PHYS_REG_MAP[element['src2']][0] = True
    PHYS_REG_MAP[element['src2']][1] = True
    PHYS_REG_MAP[element['dst']][0] = True
    PHYS_REG_MAP[element['dst']][1] = True

    return

def unmap_pregs():

    for i in range(len(toremove)):
        update_and_rename_preg_table(toremove[i]['src1'])
        update_and_rename_preg_table(toremove[i]['src2'])
        update_and_rename_preg_table(toremove[i]['dst'])

    return

def update_and_rename_preg_table(reg):
    register_used = False

    # check if any other instruction in the issue queue uses this instruction
    for i in range(len(ISSUE_QUEUE)):
        if ISSUE_QUEUE[i]['src1'] == reg or ISSUE_QUEUE[i]['src2'] == reg or ISSUE_QUEUE[i]['dst'] == reg:
            register_used = True
            break

    # if no further instructions uses the register
    if register_used == False:
        rename_reg_in_issue_queue(reg)
        PHYS_REG_MAP[reg][0] = False # set reg not active

    return

def rename_reg_in_issue_queue(preg):

    global ISSUE_QUEUE

    target_reg = -1

    for i in range(len(ISSUE_QUEUE)):
        element = ISSUE_QUEUE[i]
        if (element['src1ready'] == True and element['src2ready'] == True):
            if PHYS_REG_MAP[element['src1']][0] == False:
                target_reg = element['src1']
                break

            if PHYS_REG_MAP[element['src2']][0] == False:
                target_reg = element['src2']
                break

            if PHYS_REG_MAP[element['dst']][0] == False:
                target_reg = element['dst']
                break

    if(target_reg > -1):
        for i in range(len(ISSUE_QUEUE)):
            if ISSUE_QUEUE[i]['src1'] == target_reg:
                ISSUE_QUEUE[i]['src1'] = preg

            if ISSUE_QUEUE[i]['src2'] == target_reg:
                ISSUE_QUEUE[i]['src2'] = preg

            if ISSUE_QUEUE[i]['dst'] == target_reg:
                ISSUE_QUEUE[i]['dst'] = preg

    return


def remove_insn_from_issue_queue(i):

    ISSUE_QUEUE.remove(i)

    return

def wakeup():
    for i in range(len(ISSUE_QUEUE)):
        element = ISSUE_QUEUE[i]
        element['src1ready'] = isready(element['src1'])
        element['src2ready'] = isready(element['src2'])
    unmap_pregs()
    return

def compute_max_width(insns):
    return MAX_WIDTH

def compute_max_pregs(insns):

    pregs_used = 0

    for i in range(len(PHYS_REG_MAP)):
        if PHYS_REG_MAP[i][1] == True:
            pregs_used += 1
    
    return pregs_used

def main(insns):
    # First, rename insns to remove false dependences.
    for i in insns:
        rename(i)

    results = {}

    # Compute latency (versus serial).
    results['latency'] = compute_latency(insns)
    results['serial latency'] = len(insns)

    # Compute max machine width used (max number of insns that
    # executed in parallel).
    results['max machine width used'] = compute_max_width(insns)

    # Compute max number of pregs used.
    results['max pregs used'] = compute_max_pregs(insns)

    return repr(results)

if __name__ == "__main__":
    # Edit this line to run with different trace files (or pass a
    # filename on the command name).
    filename = "random-3ticks-3width-4pregs.insns"
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    pprint.pprint(main( eval(open(filename).read()) ))

    # Uncomment this line to run with a random trace instead.
    # pprint.pprint(main( gen_insns(5) ))

    # This code below will dump a random trace of 5 insns to the
    # terminal, so you can save it as a file and read it back in later.
    # pprint.pprint(gen_insns(5))
