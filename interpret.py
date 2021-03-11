import re
import sys
import getopt
import xml.etree.ElementTree as ET

# IPP - projekt 2
# Dominik Nejedly (xnejed09)
# Interpret XML reprezentace kodu jazyka IPPcode20

class errorCodes:
    # parametry skriptu a chyby souboru
    PAR_ERR = 10
    INPUT_FILE_ERR = 11
    OUTPUT_FILE_ERR = 12

    # chyby XML souboru
    XML_FORMAT_ERR = 31
    XML_STRUCT_LEX_SYNTAX_ERR = 32

    # behove chyby
    SEMANTIC_ERR = 52
    BAD_OPERAND_TYPE = 53
    NONEXISTENT_VAR = 54
    NONEXISTENT_FRAME = 55
    MISSING_VALUE = 56
    BAD_OPERAND_VALUE = 57
    STRING_ERR = 58

    # neovlivnitelna chyba programu
    INTERNAL_ERR = 99


# trida instrukce s konstruktorem
class instruction:
    def __init__(self, opcode):
        self.opcode = opcode


# trida argumentu s kontruktorem
class argument:
    def __init__(self, value):
        self.value = value


# trida promenne s kontruktorem
class variable:
    def __init__(self, name, varType, value):
        self.name = name
        self.varType = varType
        self.value = value


# trida jednotky datoveho zasobniku s kontruktorem
class dataStackEl:
    def __init__(self, elType, value):
        self.elType = elType
        self.value = value


# Uzavreni souboru, pracuje s globalnim deskriptorem.
def closeFile():
    global fd

    if(fd != None):
        fd.close()


# vypis na standardni chybovy vystup
def printToStderr(someStr):
    print(someStr, file = sys.stderr)


# vypis chyboveho hlaseni a ukonceni programu
def errExit(errCode, errMsg):
    closeFile()
    printToStderr("ERROR: " + errMsg)
    sys.exit(errCode)


# vypis obsahu ramce na standardni chybovy vystup
def printFrameStderr(frame, frames):
    if(len(frames[frame]) == 0):
        printToStderr("Frame is empty.")
    else:
        for var in frames[frame]:
            varType = frames[frame][var].varType
            value = frames[frame][var].value

            if(varType == None):
                varType = "None"
                value = "None"

            printToStderr(var + "\t|\t" + varType + "\t|\t" + str(value))


# nahrada ciselnych escape sekvenci za znaky
def dealWithEscape(editStr):
    escSeqList = re.findall(r'\\\d{3}', editStr)

    while(len(escSeqList) > 0):
        escSeq = escSeqList[0]
        editStr = editStr.replace(escSeq, chr(int(escSeq.replace("\\", ""))))

        while(escSeq in escSeqList):
            escSeqList.remove(escSeq)

    return editStr


# kontrola existence ramce
def frameExist(frame, frames):
    if(frames[frame] != None):
        return True

    return False


# kontrola existence promenne v urcitem ramci
def varInFrame(varName, frame, frames):
    if(varName in frames[frame]):
        return True

    return False


# Zkontroluje, zdali dana promenna ci ramec existuji.
def checkVarExistance(varName, frame, frames):
    if(not frameExist(frame, frames)):
        errExit(errorCodes.NONEXISTENT_FRAME, "Frame does not exist!")
    elif(not varInFrame(varName, frame, frames)):
        errExit(errorCodes.NONEXISTENT_VAR, "Varialbe does not exist!")


# Zkotroluje, zdali je promenna inicializovana.
def checkVarInit(varName, frame, frames):
    if(frames[frame][varName].varType == None):
        errExit(errorCodes.MISSING_VALUE, "Variable is not initialized!")


# Zkontroluje 2. argument instrukce a jeho typ.
def getArg2(instr, frames, dataType):
    if(instr.arg2.type == "var"):
        var = instr.arg2.value.split('@')
        checkVarExistance(var[1], var[0], frames)
        checkVarInit(var[1], var[0], frames)

        if(frames[var[0]][var[1]].varType != dataType):
            errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")
        value = frames[var[0]][var[1]].value
    else:
        if(instr.arg2.type != dataType):
            errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

        value = instr.arg2.value

    return value


# Zkontroluje 3. argument instrukce a jeho typ.
def getArg3(instr, frames, dataType):
    if(instr.arg3.type == "var"):
        var = instr.arg3.value.split('@')
        checkVarExistance(var[1], var[0], frames)
        checkVarInit(var[1], var[0], frames)

        if(frames[var[0]][var[1]].varType != dataType):
            errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

        value = frames[var[0]][var[1]].value
    else:
        if(instr.arg3.type != dataType):
            errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")
        value = instr.arg3.value

    return value


# Zkontroluje 2. argument instrukce a vrati jeho typ a hodnotu.
def getArg2WType(instr, frames):
    if(instr.arg2.type == "var"):
        var = instr.arg2.value.split('@')
        checkVarExistance(var[1], var[0], frames)
        checkVarInit(var[1], var[0], frames)
        dataType = frames[var[0]][var[1]].varType
        value = frames[var[0]][var[1]].value
    else:
        dataType = instr.arg2.type
        value = instr.arg2.value

    return dataType, value


# Zkontroluje 3. argument instrukce a vrati jeho typ a hodnotu.
def getArg3WType(instr, frames):
    if(instr.arg3.type == "var"):
        var = instr.arg3.value.split('@')
        checkVarExistance(var[1], var[0], frames)
        checkVarInit(var[1], var[0], frames)
        dataType = frames[var[0]][var[1]].varType
        value = frames[var[0]][var[1]].value
    else:
        dataType = instr.arg3.type
        value = instr.arg3.value

    return dataType, value


# Zkontroluje existenci a typ hodnoty na datovem zasobniku a danou hodnotu vrati.
def getDStackEl(dataStack, dataType):
    if(len(dataStack) == 0):
        errExit(errorCodes.MISSING_VALUE, "Data stack is empty!")

    dataEl = dataStack.pop()
    
    if(dataEl.elType != dataType):
        errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

    return dataEl.value


# Zkontroluje hodnotu na datovem zasobniku a vrati ji i s jejim typem.
def getDStackElWType(dataStack):
    if(len(dataStack) == 0):
        errExit(errorCodes.MISSING_VALUE, "Data stack is empty!")

    dataEl = dataStack.pop()

    return dataEl.elType, dataEl.value


# zapsani statistik do souboru
def writeStats(statsFiles, statsRecords, numOfInstr, numOfVars):
    for fileName in statsFiles:
        try:
            fd = open(fileName, "w")
        except:
            errExit(errorCodes.OUTPUT_FILE_ERR, "Can not open output statistic file!")

        for record in statsRecords:
            if(record == "vars"):
                print(numOfVars, file = fd)
            else:
                print(numOfInstr, file = fd)

        fd.close()


# kontrola spravneho zapisu promenne
def checkVar(var):
    if(re.match(r'^(GF|LF|TF)@[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$', var) == None):
        errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument invalid var name!")


# kontrola spravneho zapisu hodnoty nil
def checkNil(nil):
    if(nil != "nil"):
        errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument invalid nil value!")


# kontrola spravneho zapisu hodnoty int
def checkInt(intVal):
    if(re.match(r'^[+\-]?\d+$', intVal)):
        return True
    return False


# kontrola spravneho zapisu bool hodnoty
def checkBool(boolVal):
    if(boolVal in ["true", "false"]):
        return True
    return False


# kontrola spravneho zapisu retezce
def checkString(stringVal):
    # Pokud neni zadana hodnota, pracuje se s prazdnym retezcem.
    if(stringVal == None):
        stringVal = ""

    if(re.match(r'^([^\s\\#]|(\\\d{3}))*$', stringVal)):
        return True
    return False


# kontrola spravneho zapisu navesti
def checkLabel(label):
    if(re.match(r'^[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$', label) == None):
        errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument ivalid label name!")


# kontrola spravneho zapisu typu
def checkType(typeVal):
    if(typeVal not in ["int", "string", "bool"]):
        errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument invalid data type name!")


# funkce na kontrolu argumentu v XML
def checkXMLArgs(args, numOfArgs, expectedTypes):
    # kontrola poctu argumentu u instrukce
    if(len(args) != numOfArgs):
        errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid number of arguments!")

    expectedTags = []   # pole s ocekavanymi jmeny elementu
    ordOfArgs = []      # poradi argumentu

    # nahrani ocekavanych jmen argumentu
    for num in range(1, numOfArgs + 1):
        expectedTags.append("arg" + str(num))

    # kontrola jednotlivych argumentu
    for arg in args:
        # Argument nemuze mit dalsi potomky.
        if(len(arg) != 0):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Arguments can not have children!")

        # kotrola jmena argumentu a take duplicity jeho vyskytu
        if(arg.tag not in expectedTags):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid argument tag!")

        # kontrola atributu argumentu
        if(len(arg.attrib) != 1):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Argument has invalid number of attributes!")

        if("type" not in arg.attrib):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid argument attribute!")

        # vymazani jiz zpracovaneho argumentu
        expectedTags.remove(arg.tag)

        # ulozeni poradi argumentu
        ordOfArgs.append(arg.tag)
        
        # kotrola typu jednotlivych argumentu a take existence textoveho elementu nesouciho danou hodnotu
        if(expectedTypes[int(arg.tag[3]) - 1] == "symb"):
            if(arg.attrib["type"] == "var"):
                if(arg.text == None):
                    errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument missing name of variable!")

                checkVar(arg.text)
            elif(arg.attrib["type"] == "nil"):
                if(arg.text == None):
                    errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument missing nil value!")

                checkNil(arg.text)
            elif(arg.attrib["type"] == "int"):
                if(arg.text == None):
                    errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument missing int value!")

                if(checkInt(arg.text) == False):
                    errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument invalid int value!")
            elif(arg.attrib["type"] == "bool"):
                if(arg.text == None):
                    errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument missing bool value!")

                if(checkBool(arg.text) == False):
                    errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument invalid bool value!")
            elif(arg.attrib["type"] == "string"):
                if(checkString(arg.text) == False):
                    errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument invalid string value!")
            else:
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid XML argument type!")
        elif(expectedTypes[int(arg.tag[3]) - 1] == "var"):
            if(arg.attrib["type"] != "var"):
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid XML argument type!")

            if(arg.text == None):
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument missing name of variable!")

            checkVar(arg.text)
        elif(expectedTypes[int(arg.tag[3]) - 1] == "label"):
            if(arg.attrib["type"] != "label"):
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid XML argument type!")

            if(arg.text == None):
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument missing name of label!")
        
            checkLabel(arg.text)
        else:
            if(arg.attrib["type"] != "type"):
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid XML argument type!")

            if(arg.text == None):
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "XML argument missing type value!")

            checkType(arg.text)   

    return ordOfArgs


if __name__ == "__main__":
    # Promenna ridici uzavreni input souboru
    fd = None

    # zpracovani parametru z prikazove radky 
    try:
        opts, args = getopt.getopt(sys.argv[1:], "",["help", "source=", "input=", "stats=", "insts", "vars"])
    except:
        errExit(errorCodes.PAR_ERR, "Invalid parameter!")

    sourceFile = None
    inputFile = None
    statsFiles = []
    statsRecords = []

    # pruchod pres jednotlive argumenty, jejich kontrola a ulozeni ziskanych hodnot
    for opt, arg in opts:
        if(opt == "--help"):
            if(len(sys.argv) != 2):
                errExit(errorCodes.PAR_ERR ,"Invalid combination of parameters!")
            
            print("\nThe script loads XML representations of program, inteprets this program")
            print("using input according to parameters of command line and generate output.\n")
            print("--help\t\tprint out basic info about this script")
            print("--source=file\tinput file with XML representation of source code")
            print("--input=file\tfile with inputs for interpretation of source code")
            print("--stats=file\tfile with statistics")
            print("--insts\t\trecord number of executed instructions")
            print("--vars\t\trecord number of initialized variables\n")

            sys.exit(0)
        
        elif(opt == "--source"):
            if(sourceFile != None):
                errExit(errorCodes.PAR_ERR ,"Multiple source files!")
            sourceFile = arg
        elif(opt == "--input"):
            if(inputFile != None):
                errExit(errorCodes.PAR_ERR ,"Multiple input files!")
            inputFile = arg
        elif(opt == "--stats"):
            if(arg == sys.argv[0]):
                errExit(errorCodes.PAR_ERR ,"This script does not want to be rewrite!")
            statsFiles.append(arg)
        elif(opt == "--insts"):
            statsRecords.append("insts")
        else:
            statsRecords.append("vars")

    # Musi byt zadan alespon jeden ze souboru se vstupnim XML ci vstupem pro interpretovany program.
    if(sourceFile == None and inputFile == None):
        errExit(errorCodes.PAR_ERR ,"Missing source and input, at least one of them have to be there!")

    # Pokud jsou zadany argumenty urcujici statistiky, musi byt zadan alespon jeden soubor pro jejich zapsani.
    if(len(statsRecords) != 0 and len(statsFiles) == 0):
        errExit(errorCodes.PAR_ERR ,"Missing stats file!")

    # Pokud nebyl zadan soubor se vstupni XML reprezentaci, je tento format ocekavan na standardnim vstupu.
    if(sourceFile == None):
        sourceFile = sys.stdin


    # prace s XML
    try:
        tree = ET.parse(sourceFile)
    except IOError:
        errExit(errorCodes.INPUT_FILE_ERR, "Can not open source file!")
    except ET.ParseError:
        errExit(errorCodes.XML_FORMAT_ERR, "Invalid XML format!")

    root = tree.getroot()

    # kontrola korene stromu a jeho atributu
    if(root.tag != "program"):
        errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Root tag is not program!")

    if("language" not in root.attrib):
        errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Language attribute in root is missing!")

    if(root.attrib["language"].upper() != "IPPCODE20"):
        errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid language attribute!")

    del root.attrib["language"]

    for atrb in root.attrib:
        if(atrb not in ["name", "description"]):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid root attribute!")

    # Data slouzici k naslednemu provadeni instrukci

    orderArray = []     # pole s poradim instrukci
    fncDict = dict()    # slovnik instrukci (klicem je poradi instrukce a hodnotou jeji element)
    labelDict = dict()  # slovnik navesti

    # kontrola instrukci a jejich atributu
    for XMLInstr in root:
        if(XMLInstr.tag != "instruction"):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid instruction tag!")

        if(len(XMLInstr.attrib) != 2):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Instruction has invalid number of attributes!")

        for attrib in XMLInstr.attrib:
            if(attrib not in ["order", "opcode"]):
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid instruction attribute!")

        if(re.match(r'^\+?\d+$' ,XMLInstr.attrib["order"]) == None):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Instruction order has to be positive number!")

        order = int(XMLInstr.attrib["order"])

        # Instrukce musi mit cislo vetsi nez 0.
        if(order == 0):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Instruction order can not be zero!")

        # Cisla instrukci se nesmi opakovat.
        if(order in orderArray):
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Instruction order has to be unique!")

        opcode = XMLInstr.attrib["opcode"].upper()

        orderArray.append(order)

        # funkce bez argumentu
        if(opcode in ["CREATEFRAME", "PUSHFRAME", "POPFRAME", "RETURN", "BREAK", "CLEARS", "ADDS", "SUBS", "MULS", "IDIVS", "LTS", "GTS", "EQS", "ANDS", "ORS", "NOTS", "INT2CHARS", "STRI2INTS"]):
            if(len(XMLInstr) != 0):
                errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Invalid number of arguments!")

            fncDict[order] = instruction(opcode)
        # funkce s jednim argumentem var
        elif(opcode in ["DEFVAR", "POPS"]):
            checkXMLArgs(XMLInstr, 1, ["var"])
            fncDict[order] = instruction(opcode)
            fncDict[order].arg1 = argument(XMLInstr[0].text)
        # funkce s jednim argumentem label
        elif(opcode in ["CALL", "LABEL", "JUMP", "JUMPIFEQS", "JUMPIFNEQS"]):
            checkXMLArgs(XMLInstr, 1, ["label"])
            fncDict[order] = instruction(opcode)
            fncDict[order].arg1 = argument(XMLInstr[0].text)

            # sber navesti
            if(opcode == "LABEL"):
                labelName = XMLInstr[0].text

                # kontrola jejich unikatnosti
                if(labelName in labelDict):
                    errExit(errorCodes.SEMANTIC_ERR, "Label name has to be unique!")

                labelDict[labelName] = order
        # funkce s jednim argumentem symb
        elif(opcode in ["PUSHS", "WRITE", "EXIT", "DPRINT"]):
            checkXMLArgs(XMLInstr, 1, ["symb"])
            fncDict[order] = instruction(opcode)

            if(XMLInstr[0].attrib["type"] == "string" and XMLInstr[0].text == None):
                fncDict[order].arg1 = argument("")
            else:
                fncDict[order].arg1 = argument(XMLInstr[0].text)

            fncDict[order].arg1.type = XMLInstr[0].attrib["type"]
        # funkce s prvnim argumentem var a druhym symb
        elif(opcode in ["MOVE", "NOT", "INT2CHAR", "STRLEN", "TYPE"]):
            ordOfArgs = checkXMLArgs(XMLInstr, 2, ["var", "symb"])
            fncDict[order] = instruction(opcode)
            fncDict[order].arg1 = argument(XMLInstr[ordOfArgs.index("arg1")].text)

            if(XMLInstr[ordOfArgs.index("arg2")].attrib["type"] == "string" and XMLInstr[ordOfArgs.index("arg2")].text == None):
                fncDict[order].arg2 = argument("")
            else:
                fncDict[order].arg2 = argument(XMLInstr[ordOfArgs.index("arg2")].text)

            fncDict[order].arg2.type = XMLInstr[ordOfArgs.index("arg2")].attrib["type"]
        # funkce s prvnim argumentem var a druhym type
        elif(opcode == "READ"):
            ordOfArgs = checkXMLArgs(XMLInstr, 2, ["var", "type"])
            fncDict[order] = instruction(opcode)
            fncDict[order].arg1 = argument(XMLInstr[ordOfArgs.index("arg1")].text)
            fncDict[order].arg2 = argument(XMLInstr[ordOfArgs.index("arg2")].text)
        # funkce s prvnim argumentem var a druhym a tretim symb
        elif(opcode in ["ADD", "SUB", "MUL", "IDIV", "LT", "GT", "EQ", "AND", "OR", "STRI2INT", "CONCAT", "GETCHAR", "SETCHAR"]):
            ordOfArgs = checkXMLArgs(XMLInstr, 3, ["var", "symb", "symb"])
            fncDict[order] = instruction(opcode)
            fncDict[order].arg1 = argument(XMLInstr[ordOfArgs.index("arg1")].text)

            if(XMLInstr[ordOfArgs.index("arg2")].attrib["type"] == "string" and XMLInstr[ordOfArgs.index("arg2")].text == None):
                fncDict[order].arg2 = argument("")
            else:
                fncDict[order].arg2 = argument(XMLInstr[ordOfArgs.index("arg2")].text)

            fncDict[order].arg2.type = XMLInstr[ordOfArgs.index("arg2")].attrib["type"]

            if(XMLInstr[ordOfArgs.index("arg3")].attrib["type"] == "string" and XMLInstr[ordOfArgs.index("arg3")].text == None):
                fncDict[order].arg3 = argument("")
            else:
                fncDict[order].arg3 = argument(XMLInstr[ordOfArgs.index("arg3")].text)

            fncDict[order].arg3.type = XMLInstr[ordOfArgs.index("arg3")].attrib["type"]
        # funkce s prvnim argumentem label a druhym a tretim symb
        elif(opcode in ["JUMPIFEQ", "JUMPIFNEQ"]):
            ordOfArgs = checkXMLArgs(XMLInstr, 3, ["label", "symb", "symb"])
            fncDict[order] = instruction(opcode)
            fncDict[order].arg1 = argument(XMLInstr[ordOfArgs.index("arg1")].text)

            if(XMLInstr[ordOfArgs.index("arg2")].attrib["type"] == "string" and XMLInstr[ordOfArgs.index("arg2")].text == None):
                fncDict[order].arg2 = argument("")
            else:
                fncDict[order].arg2 = argument(XMLInstr[ordOfArgs.index("arg2")].text)

            fncDict[order].arg2.type = XMLInstr[ordOfArgs.index("arg2")].attrib["type"]

            if(XMLInstr[ordOfArgs.index("arg3")].attrib["type"] == "string" and XMLInstr[ordOfArgs.index("arg3")].text == None):
                fncDict[order].arg3 = argument("")
            else:
                fncDict[order].arg3 = argument(XMLInstr[ordOfArgs.index("arg3")].text)

            fncDict[order].arg3.type = XMLInstr[ordOfArgs.index("arg3")].attrib["type"]
        else:
            errExit(errorCodes.XML_STRUCT_LEX_SYNTAX_ERR, "Unknown operation code!")

    # nastaveni vstupu pro pripadne cteni
    if(inputFile != None):
        try:
            fd = open(inputFile)
        except:
            errExit(errorCodes.INPUT_FILE_ERR, "Can not open input file!")

        sys.stdin = fd


    # usporadani instrukci podle poradi
    orderArray.sort()

    # provadeni programu
    numOfExecInstr = 0
    numOfDefVars = 0

    frames = dict()
    frames["GF"] = dict()
    frames["LF"] = None
    frames["TF"] = None

    frameStack = []
    dataStack = []
    callStack = []

    i = 0

    while(i < len(orderArray)):

        # aktualni instrukce
        instr = fncDict[orderArray[i]]
        
        # vytvori docasny ramec
        if(instr.opcode == "CREATEFRAME"):
            frames["TF"] = dict()
        # ramec docasny se stava ramcem lokalnim
        elif(instr.opcode == "PUSHFRAME"):
            if(frames["TF"] == None):
                errExit(errorCodes.NONEXISTENT_FRAME, "Temporary frame does not exist!")

            frameStack.append(frames["TF"])
            frames["LF"] = frames["TF"]
            frames["TF"] = None
        # lokalni ramec je presunut do docasneho ramce
        elif(instr.opcode == "POPFRAME"):
            if(frames["LF"] == None):
                errExit(errorCodes.NONEXISTENT_FRAME, "Local frame does not exist!")

            frames["TF"] = frames["LF"]
            frameStack.pop()

            if(len(frameStack) == 0):
                frames["LF"] == None
            else:
                frames["LF"] = frameStack.pop()
                frameStack.append(frames["LF"])
        # navrat za misto volani
        elif(instr.opcode == "RETURN"):
            if(len(callStack) == 0):
                errExit(errorCodes.MISSING_VALUE, "Call stack is empty!")

            i = callStack.pop()
        # vypis stavu interpretu na standardni chybovy vystup
        elif(instr.opcode == "BREAK"):
            line = i + 1
            
            printToStderr("\n\ninstruction number: " + str(line))
            printToStderr("instruction order: " + str(orderArray[i]))
            printToStderr("number of executed instructions: " + str(numOfExecInstr) + "\n\n")

            printToStderr("GLOBAL FRAME CONTENT(variable|type|value)")
            printToStderr("-----------------------------------------")
            printFrameStderr("GF", frames)
            printToStderr("\n")

            printToStderr("LOCAL FRAME CONTENT(variable|type|value)")
            printToStderr("----------------------------------------")

            if(frames["LF"] == None):
                printToStderr("Frame does not exit.")
            else:
                printFrameStderr("LF", frames)

            printToStderr("\n")

            printToStderr("TEMPORARY FRAME CONTENT(variable|type|value)")
            printToStderr("--------------------------------------------")

            if(frames["TF"] == None):
                printToStderr("Frame does not exit.")
            else:
                printFrameStderr("TF", frames)
            
            printToStderr("\n")
        # Smaze cely obsah datoveho zasobniku.
        elif(instr.opcode == "CLEARS"):
            while(len(dataStack) > 0):
                dataStack.pop()
        # Vybere z datoveho zasobniku dve hodnoty, secte je a vysledek ulozi na vrchol zasobniku.
        elif(instr.opcode == "ADDS"):
            value2 = int(getDStackEl(dataStack, "int"))
            value1 = int(getDStackEl(dataStack, "int"))

            result = value1 + value2

            dataStack.append(dataStackEl("int", result))
        # Vybere z datoveho zasobniku dve hodnoty, od prvni odecte druhou a vysledek vrati na vrchol zasobniku.
        elif(instr.opcode == "SUBS"):
            value2 = int(getDStackEl(dataStack, "int"))
            value1 = int(getDStackEl(dataStack, "int"))

            result = value1 - value2

            dataStack.append(dataStackEl("int", result))
        # Vybere z datoveho zasobniku dve hodnoty, vynasobi je a vysledek ulozi na vrchol zasobniku.
        elif(instr.opcode == "MULS"):
            value2 = int(getDStackEl(dataStack, "int"))
            value1 = int(getDStackEl(dataStack, "int"))

            result = value1 * value2

            dataStack.append(dataStackEl("int", result))
        # Vybere z datoveho zasobniku dve hodnoty, prvni vydeli druhou a vysledek ulozi na vrchol zasobniku.
        elif(instr.opcode == "IDIVS"):
            value2 = int(getDStackEl(dataStack, "int"))
            value1 = int(getDStackEl(dataStack, "int"))

            if(value2 == 0):
                errExit(errorCodes.BAD_OPERAND_VALUE, "Division by zero!")

            result = value1 // value2

            dataStack.append(dataStackEl("int", result))
        # Vybere z datoveho zasobniku dve hodnoty a zjisti, zdali je prvni z nich mensi nez druha.
        elif(instr.opcode == "LTS"):
            type2, value2 = getDStackElWType(dataStack)

            if(type2 == "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

            value1 = getDStackEl(dataStack, type2)

            if(type2 == "int"):
                value2 = int(value2)
                value1 = int(value1)

            if(value1 < value2):
                dataStack.append(dataStackEl("bool", "true"))
            else:
                dataStack.append(dataStackEl("bool", "false"))
        # Vybere z datoveho zasobniku dve hodnoty a zjisti, zdali je prvni z nich vetsi nez druha.
        elif(instr.opcode == "GTS"):
            type2, value2 = getDStackElWType(dataStack)

            if(type2 == "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

            value1 = getDStackEl(dataStack, type2)

            if(type2 == "int"):
                value2 = int(value2)
                value1 = int(value1)

            if(value1 > value2):
                dataStack.append(dataStackEl("bool", "true"))
            else:
                dataStack.append(dataStackEl("bool", "false"))
        # Vybere z datoveho zasobniku dve hodnoty a zjisti, zdali jsou stejne.
        elif(instr.opcode == "EQS"):
            type2, value2 = getDStackElWType(dataStack)
            type1, value1 = getDStackElWType(dataStack)

            if(type1 == type2):
                if(type1 == "int"):
                    value1 = int(value1)
                    value2 = int(value2)

                if(value1 == value2):
                    dataStack.append(dataStackEl("bool", "true"))
                else:
                    dataStack.append(dataStackEl("bool", "false"))
            elif(type1 == "nil" or type2 == "nil"):
                dataStack.append(dataStackEl("bool", "false"))
            else:
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")
        # Vybere z datoveho zasobniku dve hodnoty a aplikuje na ne logickou konjunkci.
        elif(instr.opcode == "ANDS"):
            value2 = getDStackEl(dataStack, "bool")
            value1 = getDStackEl(dataStack, "bool")

            if(value1 == "true" and value2 == "true"):
                dataStack.append(dataStackEl("bool", "true"))
            else:
                dataStack.append(dataStackEl("bool", "false"))
        # Vybere z datoveho zasobniku dve hodnoty a aplikuje na ne logickou disjunkci.
        elif(instr.opcode == "ORS"):
            value2 = getDStackEl(dataStack, "bool")
            value1 = getDStackEl(dataStack, "bool")

            if(value1 == "true" or value2 == "true"):
                dataStack.append(dataStackEl("bool", "true"))
            else:
                dataStack.append(dataStackEl("bool", "false"))
        # Vybere z datoveho zasobniku hodnotu, zneguje ji a ulozi opet na zasobnik.
        elif(instr.opcode == "NOTS"):
            value = getDStackEl(dataStack, "bool")

            if(value == "true"):
                dataStack.append(dataStackEl("bool", "false"))
            else:
                dataStack.append(dataStackEl("bool", "true"))
        # Vybere z datoveho zasobniku ciselnou hodnotu a prevede ji na UNICODE znak.
        elif(instr.opcode == "INT2CHARS"):
            value = int(getDStackEl(dataStack, "int"))

            try:
                dataStack.append(dataStackEl("string", chr(value)))
            except:
                errExit(errorCodes.STRING_ERR, "Invalid ordinal value of character in UNICODE!")
        # Vybere z datoveho zasobniku dve hodnoty a ulozi na jeho vrchol ordinalni hodnotu znaku na urcite pozici v retezci.
        elif(instr.opcode == "STRI2INTS"):
            value2 = int(getDStackEl(dataStack, "int"))
            value1 = dealWithEscape(getDStackEl(dataStack, "string"))

            if(value2 < 0 or value2 >= len(value1)):
                errExit(errorCodes.STRING_ERR, "Index out of range!")

            dataStack.append(dataStackEl("int", ord(value1[value2])))
        # definice promenne v danem ramci
        elif(instr.opcode == "DEFVAR"):
            var = instr.arg1.value.split('@')

            if(not frameExist(var[0], frames)):
                errExit(errorCodes.NONEXISTENT_FRAME, "Frame does not exist!")
            elif(varInFrame(var[1], var[0], frames)):
                errExit(errorCodes.SEMANTIC_ERR, "Redefinition of variable!")
            else:
                frames[var[0]][var[1]] = variable(var[1], None, None)

            numOfDefVars += 1
        # Vyjme hodnotu z vrcholu datoveho zasobniku a ulozi ji do promenne.
        elif(instr.opcode == "POPS"):
            if(len(dataStack) == 0):
                errExit(errorCodes.MISSING_VALUE, "Data stack is empty!")
            else:
                var = instr.arg1.value.split('@')
                checkVarExistance(var[1], var[0], frames)

                dataEl = dataStack.pop()

                frames[var[0]][var[1]].varType = dataEl.elType
                frames[var[0]][var[1]].value = dataEl.value
        # skok na zadanou pozici s ulozenym navratem
        elif(instr.opcode == "CALL"):
            if(instr.arg1.value not in labelDict):
                errExit(errorCodes.SEMANTIC_ERR, "Undefined label!")

            callStack.append(i)     
            i = orderArray.index(labelDict[instr.arg1.value]) - 1
        # oznaceni navesti, vse vyreseno pred interpretaci
        elif(instr.opcode == "LABEL"):
            pass
        # skok bez navratu
        elif(instr.opcode == "JUMP"):
            if(instr.arg1.value not in labelDict):
                errExit(errorCodes.SEMANTIC_ERR, "Undefined label!")

            i = orderArray.index(labelDict[instr.arg1.value]) - 1
        # Zasobnikova verze podmineneho skoku, ktery se vykona, pokud se hodnoty a typy operandu na datovem zasobniku rovnaji.
        elif(instr.opcode == "JUMPIFEQS"):
            if(instr.arg1.value not in labelDict):
                errExit(errorCodes.SEMANTIC_ERR, "Undefined label!")

            type2, value2 = getDStackElWType(dataStack)
            type1, value1 = getDStackElWType(dataStack)

            if(type1 == type2):
                if(type1 == "int"):
                    value1 = int(value1)
                    value2 = int(value2)

                if(value1 == value2):
                    i = orderArray.index(labelDict[instr.arg1.value]) - 1
            elif(type1 != "nil" and type2 != "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")
        # Zasobnikova verze podmineneho skoku, ktery se vykona, pokud se hodnoty nebo typy operandu na datovem zasobniku nerovnaji.
        elif(instr.opcode == "JUMPIFNEQS"):
            if(instr.arg1.value not in labelDict):
                errExit(errorCodes.SEMANTIC_ERR, "Undefined label!")

            type2, value2 = getDStackElWType(dataStack)
            type1, value1 = getDStackElWType(dataStack)

            if(type1 == type2):
                if(type1 == "int"):
                    value1 = int(value1)
                    value2 = int(value2)

                if(value1 != value2):
                    i = orderArray.index(labelDict[instr.arg1.value]) - 1
            elif(type1 != "nil" and type2 != "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")
            else:
                i = orderArray.index(labelDict[instr.arg1.value]) - 1
        # Ulozi hodnotu na datovy zasobnik.
        elif(instr.opcode == "PUSHS"):
            if(instr.arg1.type == "var"):
                var = instr.arg1.value.split('@')
                checkVarExistance(var[1], var[0], frames)
                checkVarInit(var[1], var[0], frames)

                dataStack.append(dataStackEl(frames[var[0]][var[1]].varType, frames[var[0]][var[1]].value))
            else:
                dataStack.append(dataStackEl(instr.arg1.type, instr.arg1.value))
        # Vypise hodnotu na standardni vytup.
        elif(instr.opcode == "WRITE"):
            if(instr.arg1.type == "var"):
                var = instr.arg1.value.split('@')
                checkVarExistance(var[1], var[0], frames)
                checkVarInit(var[1], var[0], frames)

                dataType = frames[var[0]][var[1]].varType
                value = frames[var[0]][var[1]].value
            else:
                dataType = instr.arg1.type
                value = instr.arg1.value

            if(dataType == "int"):
                print(int(value), end = '')
            elif(dataType == "bool"):
                print(value, end = '')
            elif(dataType == "string"):
                print(dealWithEscape(value), end = '')
            else:
                print("", end = '')
        # Ukonci interpretaci s navratovym kodem.
        elif(instr.opcode == "EXIT"):
            if(instr.arg1.type == "var"):
                var = instr.arg1.value.split('@')
                checkVarExistance(var[1], var[0], frames)
                checkVarInit(var[1], var[0], frames)

                if(frames[var[0]][var[1]].varType != "int"):
                    errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

                value = int(frames[var[0]][var[1]].value)
            else:
                if(instr.arg1.type != "int"):
                    errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

                value = int(instr.arg1.value)

            if(value < 0 or value > 49):
                errExit(errorCodes.BAD_OPERAND_VALUE, "Invalid operand value!")

            if(len(statsFiles) != 0):
                writeStats(statsFiles, statsRecords, numOfExecInstr + 1, numOfDefVars)

            closeFile()
            sys.exit(value)  
        # Vypise zadanou hodnotu na standardni chybovy vystup.
        elif(instr.opcode == "DPRINT"):
            if(instr.arg1.type == "var"):
                var = instr.arg1.value.split('@')
                checkVarExistance(var[1], var[0], frames)
                checkVarInit(var[1], var[0], frames)

                dataType = frames[var[0]][var[1]].varType
                value = frames[var[0]][var[1]].value
            else:
                dataType = instr.arg1.type
                value = instr.arg1.value

            if(dataType == "int"):
                print(int(value), end = '', file = sys.stderr)
            elif(dataType == "bool"):
                print(value, end = '', file = sys.stderr)
            elif(dataType == "string"):
                print(dealWithEscape(value), end = '', file = sys.stderr)
            else:
                print("", end = '', file = sys.stderr)
        # Zkopiruje hodnotu 2. argumentu do promenne v 1. argumentu.
        elif(instr.opcode == "MOVE"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            dataType, value = getArg2WType(instr, frames)

            frames[var[0]][var[1]].varType = dataType
            frames[var[0]][var[1]].value = value
        # Aplikuje negaci na bool hodnotu v 2. argumentu a vysledek zapise do promenne v 1. argumentu.
        elif(instr.opcode == "NOT"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value = getArg2(instr, frames, "bool")

            if(value == "true"):
                value = "false"
            else:
                value = "true"

            frames[var[0]][var[1]].varType = "bool"
            frames[var[0]][var[1]].value = value
        # prevod ciselne hodnoty na UNICODE znak
        elif(instr.opcode == "INT2CHAR"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value = int(getArg2(instr, frames, "int"))

            try:
                frames[var[0]][var[1]].value = chr(value)
            except:
                errExit(errorCodes.STRING_ERR, "Invalid ordinal value of character in UNICODE!")

            frames[var[0]][var[1]].varType = "string"
        # Zjisti delku retezce a ulozi ji do promenne.
        elif(instr.opcode == "STRLEN"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value = getArg2(instr, frames, "string")
            strLen = len(dealWithEscape(value))

            frames[var[0]][var[1]].varType = "int"
            frames[var[0]][var[1]].value = strLen
        # Zjisti typ symbolu a zapise ho do promenne.
        elif(instr.opcode == "TYPE"):
            var1 = instr.arg1.value.split('@')
            checkVarExistance(var1[1], var1[0], frames)

            if(instr.arg2.type == "var"):
                var2 = instr.arg2.value.split('@')
                checkVarExistance(var2[1], var2[0], frames)

                if(frames[var2[0]][var2[1]].varType == None):
                    value = ""
                else:
                    value = frames[var2[0]][var2[1]].varType
            else:
                value = instr.arg2.type

            frames[var1[0]][var1[1]].varType = "string"
            frames[var1[0]][var1[1]].value = value
        # Nacte hodnotu dle zadaneho typu a ulozi ji do promenne.
        elif(instr.opcode == "READ"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            dataType = instr.arg2.value

            try:
                value = input()
            except:
                dataType = "nil"

            if(dataType == "int"):
                try:
                    value = int(value)
                except:
                    dataType == "nil"
            elif(dataType == "bool"):
                value = value.lower()

                if(value != "true"):
                    value = "false"

            if(dataType == "nil"):
                value = "nil"

            frames[var[0]][var[1]].varType = dataType
            frames[var[0]][var[1]].value = value
        # Secte dva symboly a vyslednou hodnotu ulozi do promenne.
        elif(instr.opcode == "ADD"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = int(getArg2(instr, frames, "int"))
            value2 = int(getArg3(instr, frames, "int"))

            result = value1 + value2

            frames[var[0]][var[1]].varType = "int"
            frames[var[0]][var[1]].value = result
        # Odecte symbol 2 od symbolu 1 a vysledek ulozi do promenne.
        elif(instr.opcode == "SUB"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = int(getArg2(instr, frames, "int"))
            value2 = int(getArg3(instr, frames, "int"))

            result = value1 - value2

            frames[var[0]][var[1]].varType = "int"
            frames[var[0]][var[1]].value = result
        # Vynasobi dva symboly a vysledek ulozi do promenne.
        elif(instr.opcode == "MUL"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = int(getArg2(instr, frames, "int"))
            value2 = int(getArg3(instr, frames, "int"))

            result = value1 * value2

            frames[var[0]][var[1]].varType = "int"
            frames[var[0]][var[1]].value = result
        # Celociselne vydeli hodnotu symb 1 hodnotou symb 2 a vysledek ulozi do promenne.
        elif(instr.opcode == "IDIV"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = int(getArg2(instr, frames, "int"))
            value2 = int(getArg3(instr, frames, "int"))

            if(value2 == 0):
                errExit(errorCodes.BAD_OPERAND_VALUE, "Division by zero!")

            result = value1 // value2

            frames[var[0]][var[1]].varType = "int"
            frames[var[0]][var[1]].value = result
        # Zjisti, zdali je hodnota symbolu 1 mensi nez hodnota symbolu 2.
        elif(instr.opcode == "LT"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            type1, value1 = getArg2WType(instr, frames)

            if(type1 == "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

            value2 = getArg3(instr, frames, type1)

            if(type1 == "int"):
                value1 = int(value1)
                value2 = int(value2)

            if(value1 < value2):
                frames[var[0]][var[1]].value = "true"
            else:
                frames[var[0]][var[1]].value = "false"

            frames[var[0]][var[1]].varType = "bool"
        # Zjisti, zdali je hodnota symbolu 1 vetsi nez hodnota symbolu 2.
        elif(instr.opcode == "GT"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            type1, value1 = getArg2WType(instr, frames)

            if(type1 == "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

            value2 = getArg3(instr, frames, type1)

            if(type1 == "int"):
                value1 = int(value1)
                value2 = int(value2)

            if(value1 > value2):
                frames[var[0]][var[1]].value = "true"
            else:
                frames[var[0]][var[1]].value = "false"

            frames[var[0]][var[1]].varType = "bool"
        # Zjisti, zdali je hodnota symbolu 1 stejna jako hodnota symbolu 2.
        elif(instr.opcode == "EQ"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            type1, value1 = getArg2WType(instr, frames)
            type2, value2 = getArg3WType(instr, frames)

            frames[var[0]][var[1]].value = "false"

            if(type1 == type2):
                if(type1 == "int"):
                    value1 = int(value1)
                    value2 = int(value2)

                if(value1 == value2):
                    frames[var[0]][var[1]].value = "true"           
            elif(type1 != "nil" and type2 != "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

            frames[var[0]][var[1]].varType = "bool"
        # Aplikuje konjunkci na operandy a vysledek ulozi do promenne.
        elif(instr.opcode == "AND"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = getArg2(instr, frames, "bool")
            value2 = getArg3(instr, frames, "bool")

            if(value1 == "true" and value2 == "true"):
                frames[var[0]][var[1]].value = "true"
            else:
                frames[var[0]][var[1]].value = "false"

            frames[var[0]][var[1]].varType = "bool"
        # Aplikuje disjunkci na operandy a vysledek ulozi do promenne.
        elif(instr.opcode == "OR"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = getArg2(instr, frames, "bool")
            value2 = getArg3(instr, frames, "bool")

            if(value1 == "true" or value2 == "true"):
                frames[var[0]][var[1]].value = "true"
            else:
                frames[var[0]][var[1]].value = "false"

            frames[var[0]][var[1]].varType = "bool"
        # Ulozi do promenne ordinalni hodnotu znaku na urcite pozici v retezci.
        elif(instr.opcode == "STRI2INT"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = dealWithEscape(getArg2(instr, frames, "string"))
            value2 = int(getArg3(instr, frames, "int"))

            if(value2 < 0 or value2 >= len(value1)):
                errExit(errorCodes.STRING_ERR, "Index out of range!")

            frames[var[0]][var[1]].varType = "int"
            frames[var[0]][var[1]].value = ord(value1[value2])
        # Ulozi do promenne konkatenaci dvou retezcovych operandu.
        elif(instr.opcode == "CONCAT"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = getArg2(instr, frames, "string")
            value2 = getArg3(instr, frames, "string")

            result = value1 + value2

            frames[var[0]][var[1]].varType = "string"
            frames[var[0]][var[1]].value = result
        # Ulozi do promenne znak na urcite pozici v retezci.
        elif(instr.opcode == "GETCHAR"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)

            value1 = dealWithEscape(getArg2(instr, frames, "string"))
            value2 = int(getArg3(instr, frames, "int"))

            if(value2 < 0 or value2 >= len(value1)):
                errExit(errorCodes.STRING_ERR, "Index out of range!")

            frames[var[0]][var[1]].varType = "string"
            frames[var[0]][var[1]].value = value1[value2]
        # Zmeni znak na urcite pozici v retezci.
        elif(instr.opcode == "SETCHAR"):
            var = instr.arg1.value.split('@')
            checkVarExistance(var[1], var[0], frames)
            checkVarInit(var[1], var[0], frames)

            if(frames[var[0]][var[1]].varType != "string"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")

            editStr = dealWithEscape(frames[var[0]][var[1]].value)
            value1 = int(getArg2(instr, frames, "int"))
            value2 = dealWithEscape(getArg2(instr, frames, "string"))

            if(len(value2) == 0):
                errExit(errorCodes.STRING_ERR, "Replacement is empty!")

            if(value1 < 0 or value1 >= len(editStr)):
                errExit(errorCodes.STRING_ERR, "Index out of range!")

            editStr[value1] = value2[0]
            frames[var[0]][var[1]].value = editStr
        # Skok na navesti, pokud se hodnoty zbyvajicich dvou operandu rovnaji.
        elif(instr.opcode == "JUMPIFEQ"):
            if(instr.arg1.value not in labelDict):
                errExit(errorCodes.SEMANTIC_ERR, "Undefined label!")

            type1, value1 = getArg2WType(instr, frames)
            type2, value2 = getArg3WType(instr, frames)

            if(type1 == type2):
                if(type1 == "int"):
                    value1 = int(value1)
                    value2 = int(value2)

                if(value1 == value2):
                    i = orderArray.index(labelDict[instr.arg1.value]) - 1
            elif(type1 != "nil" and type2 != "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")
        # Skok na navesti, pokud jsou hodnoty zbyvajicich dvou operandu ruzne.
        else:
            if(instr.arg1.value not in labelDict):
                errExit(errorCodes.SEMANTIC_ERR, "Undefined label!")

            type1, value1 = getArg2WType(instr, frames)
            type2, value2 = getArg3WType(instr, frames)

            if(type1 == type2):
                if(type1 == "int"):
                    value1 = int(value1)
                    value2 = int(value2)

                if(value1 != value2):
                    i = orderArray.index(labelDict[instr.arg1.value]) - 1
            elif(type1 != "nil" and type2 != "nil"):
                errExit(errorCodes.BAD_OPERAND_TYPE, "Incorrect operand type!")
            else:
                i = orderArray.index(labelDict[instr.arg1.value]) - 1

        numOfExecInstr += 1
        i += 1

    closeFile()

    # vypis statistik do souboru
    if(len(statsFiles) != 0):
        writeStats(statsFiles, statsRecords, numOfExecInstr, numOfDefVars)

    sys.exit(0)