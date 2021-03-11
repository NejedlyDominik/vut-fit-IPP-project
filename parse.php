<?php

/**
 * IPP - projekt 1
 * 
 * Dominik Nejedly (xnejed09)
 * 
 * Prevod kodu IPPcode20 na jeho XML reprezentaci.
 */

ini_set('display_errors', 'stderr');

// navratove hodnoty
const SUCCESS = 0;

const PARAM_ERROR = 10;
const OUTPUT_ERROR = 12;

const MISSING_HEADER = 21;
const INCORRECT_CODE = 22;
const LEX_OR_SYNTAX_ERROR = 23;

// nastaveni xml
$xmlDoc = createXML();
$xmlRoot = setXMLRoot();

// uchovani nekterych potrebnych hodnot
$stats = false;

$comments = 0;
$numOfInstructions = 0;
$jumpRelated = 0;

$statArgs = array();
$filenames = array();
$labelArray = array();

// jmeno tohoto souboru
$thisFile = $argv[0];

// zpracovani parametru
array_shift($argv);

foreach($argv as $arg)
{
    if($arg == "--help" || $arg == "-h")
    {
        if($argc != 2)
        {
            fprintf(STDERR, "Nepodporovana kombinace parametru!\n");
            exit(PARAM_ERROR);
        }

        echo "\nTento skript typu filtr (parse.php v jazyce PHP 7.4)\n";
        echo "nacte ze standardniho vstupu zdrojovy kod v IPPcode20,\n";
        echo "zkontroluje lexikalni a syntaktickou spravnost kodu\n";
        echo "a vypise na standardni vystup XML reprezentaci programu.\n";
        echo "\n--help|-h\t\tvypis napovedy\n";
        echo "(--stats|-s)=file\tvystupni soubor se statistikami\n";
        echo "--loc|-lc\t\tpocet radku s instrukcemi\n";
        echo "--comments|-c\t\tpocet radku s kometari\n";
        echo "--labels|-lb\t\tpocet unikatnich navesti\n";
        echo "--jumps|-j\t\tpocet skoku, volani a navratu\n\n";

        exit(SUCCESS);
    }
    elseif(preg_match('/^(--stats|-s)=([^="]*|"[^="]*")$/', $arg))
    {
        $filename = preg_replace('/^(--stats|-s)=/', "", $arg);

        if($filename == "")
        {
            fprintf(STDERR, "Jmenem vystupniho souboru nemuze byt prazdny retezec!\n");
            exit(PARAM_ERROR);
        }
        elseif($filename == $thisFile)
        {
            fprintf(STDERR, "Tento skript nechce byt prepsan!\n");
            exit(PARAM_ERROR);
        }

        if(!in_array($filename, $filenames))
        {
            array_push($filenames, $filename);
        }

        if(!$stats)
        {
            $stats = true;
        }
    }
    elseif($arg == '--loc' || $arg == '-lc')
    {
        array_push($statArgs, 'loc');
    }
    elseif($arg == '--comments' || $arg == '-c')
    {
        array_push($statArgs, 'comments');
    }
    elseif($arg == '--labels' || $arg == '-lb')
    {
        array_push($statArgs, 'labels');
    }
    elseif($arg == '--jumps' || $arg == '-j')
    {
        array_push($statArgs, 'jumps');
    }
    else
    {
        fprintf(STDERR, "Neznamy prepinac ($arg)!\n");
        exit(PARAM_ERROR);
    }   
}

// Kontrola, zdal byl zadan vystupni soubor pro statistiky, pokud byl definovan jejich format.
if((count($statArgs) != 0) && !$stats)
{
    fprintf(STDERR, "Tato kombinace prepinacu vyzaduje zadani vystupniho souboru!\n");
    exit(PARAM_ERROR);
}


// nacteni a kotrola hlavicky vstupniho kodu
$line = getCodeLine();

if(!preg_match('/^\s*\.IPPCODE20\s*$/', strtoupper($line)))
{
    fprintf(STDERR, "Chybna ci chybejici hlavicka ve zdrojovem kodu!\n");
    exit(MISSING_HEADER);
}

// lexikalni a syntakticka kontrola vstupniho kodu
while($line = getCodeLine())
{
    $numOfInstructions++;

    // rozdeleni nacteneho radku na slova
    $words = preg_split("/\s+/", $line);

    // Prvni z nich musi byt operacni kod a podle nej se rozhodne nasledujici tok programu.
    switch($words[0] = strtoupper($words[0]))
    {
        // funkce bez parametru
        case 'CREATEFRAME':
        case 'PUSHFRAME':
        case 'POPFRAME':
        case 'RETURN':
        case 'BREAK':
            // kontrola poctu parametru funkce
            if(count($words) != 1)
            {
                fprintf(STDERR, "Chybny pocet argumentu. Funkce $words[0] neprijima zadne parametry!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }

            addXMLInstruction($numOfInstructions, $words[0]);

            // pocitani vyskytu RETURN do statistik
            if($words[0] == 'RETURN')
            {
                $jumpRelated++; 
            }

            break;
        // funkce s jednim parametrem var
        case 'DEFVAR':
        case 'POPS':
            if(count($words) != 2)
            {
                fprintf(STDERR, "Chybny pocet argumentu. Funkce $words[0] prijima jeden parametr!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            // kontrola typu parametru funkce
            elseif(checkVar($words[1]))
            {
                addXMLArgument(addXMLInstruction($numOfInstructions, $words[0]), 1, 'var', htmlspecialchars($words[1]));
            }
            else
            {
                fprintf(STDERR, "Chybny format zapisu promenne ($words[1])!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            break;
        // funkce s jednim parametrem label
        case 'CALL':
        case 'LABEL':
        case 'JUMP':
            if(count($words) != 2)
            {
                fprintf(STDERR, "Chybny pocet argumentu. Funkce $words[0] prijima jeden parametr!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            elseif(checkLabel($words[1]))
            {
                addXMLArgument(addXMLInstruction($numOfInstructions, $words[0]), 1, 'label', htmlspecialchars($words[1]));

                // pocitani poctu LABEL(unikatnich), pripadne funkci skoku do statistik
                if($words[0] == 'LABEL')
                {
                    if(!in_array($words[1], $labelArray))
                    {
                        array_push($labelArray, $words[1]);
                    }
                }
                elseif($words[0] == 'CALL' || $words[0] == 'JUMP')
                {
                    $jumpRelated++;
                }
            }
            else
            {
                fprintf(STDERR, "Chybny format zapisu navesti ($words[1])!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            break;
        // funkce s jednim parametrem symb
        case 'PUSHS':
        case 'WRITE':
        case 'EXIT':
        case 'DPRINT':
            if(count($words) != 2)
            {
                fprintf(STDERR, "Chybny pocet argumentu. Funkce $words[0] prijima jeden parametr!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            elseif($symb = checkSymb($words[1]))
            {
                addXMLArgument(addXMLInstruction($numOfInstructions, $words[0]), 1, $symb, htmlspecialchars(dealWithConst($words[1])));
            }
            else
            {
                fprintf(STDERR, "Chybny format zapisu promenne/konstanty ($words[1])!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            break;
        // funkce s prvnim parametrem var a druhym symb
        case 'MOVE':
        case 'NOT':
        case 'INT2CHAR':
        case 'STRLEN':
        case 'TYPE':
            if(count($words) != 3)
            {
                fprintf(STDERR, "Chybny pocet argumentu. Funkce $words[0] prijima dva parametry!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            elseif(checkVar($words[1]) && ($symb = checkSymb($words[2])))
            {
                // pridani funkce s parametry do vystupniho XML
                $instruction = addXMLInstruction($numOfInstructions, $words[0]);
                addXMLArgument($instruction, 1, 'var', htmlspecialchars($words[1]));
                addXMLArgument($instruction, 2, $symb, htmlspecialchars(dealWithConst($words[2])));
            }
            else
            {
                fprintf(STDERR, "Chybny format zapisu parametru funkce $words[0]!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            break;
        // funkce s prvnim parametrem var a druhym type
        case 'READ':
            if(count($words) != 3)
            {
                fprintf(STDERR, "Chybny pocet argumentu. Funkce $words[0] prijima dva parametry!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            elseif(checkVar($words[1]) && checkType($words[2]))
            {
                $instruction = addXMLInstruction($numOfInstructions, $words[0]);
                addXMLArgument($instruction, 1, 'var', htmlspecialchars($words[1]));
                addXMLArgument($instruction, 2, 'type', $words[2]);
            }
            else
            {
                fprintf(STDERR, "Chybny format zapisu parametru funkce $words[0]!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            break;
        // funkce s prvnim parametrem var a druhym a tretim symb
        case 'ADD':
        case 'SUB':
        case 'MUL':
        case 'IDIV':
        case 'LT':
        case 'GT':
        case 'EQ':
        case 'AND':
        case 'OR':
        case 'STR2INT':
        case 'CONCAT':
        case 'GETCHAR':
        case 'SETCHAR':
            if(count($words) != 4)
            {
                fprintf(STDERR, "Chybny pocet argumentu. Funkce $words[0] prijima tri parametry!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            elseif(checkVar($words[1]) && ($symb1 = checkSymb($words[2])) && ($symb2 = checkSymb($words[3])))
            {
                $instruction = addXMLInstruction($numOfInstructions, $words[0]);
                addXMLArgument($instruction, 1, 'var', htmlspecialchars($words[1]));
                addXMLArgument($instruction, 2, $symb1, htmlspecialchars(dealWithConst($words[2])));
                addXMLArgument($instruction, 3, $symb2, htmlspecialchars(dealWithConst($words[3])));
            }
            else
            {
                fprintf(STDERR, "Chybny format zapisu parametru funkce $words[0]!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            break;
        // funkce s prvnim parametrem label a druhym a tretim symb
        case 'JUMPIFEQ':
        case 'JUMPIFNEQ':
            if(count($words) != 4)
            {
                fprintf(STDERR, "Chybny pocet argumentu. Funkce $words[0] prijima tri parametry!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            elseif(checkLabel($words[1]) && ($symb1 = checkSymb($words[2])) && ($symb2 = checkSymb($words[3])))
            {
                $instruction = addXMLInstruction($numOfInstructions, $words[0]);
                addXMLArgument($instruction, 1, 'label', htmlspecialchars($words[1]));
                addXMLArgument($instruction, 2, $symb1, htmlspecialchars(dealWithConst($words[2])));
                addXMLArgument($instruction, 3, $symb2, htmlspecialchars(dealWithConst($words[3])));

                $jumpRelated++;
            }
            else
            {
                fprintf(STDERR, "Chybny format zapisu parametru funkce $words[0]!\n");
                exit(LEX_OR_SYNTAX_ERROR);
            }
            break;
        // neznamy operacni kod
        default:
            fprintf(STDERR, "Nezname klicove slovo ($words[0])!\n");
            exit(INCORRECT_CODE);
    }
}

// Vypis statistik do souboru
if($stats)
{
    foreach($filenames as $filename)
    {
        // kontrola uspesneho otevreni souboru
        if(!($file = fopen($filename, "w")))
        {
            fprintf(STDERR, "Soubor $filename se nepodarilo otevrit!\n");
            exit(OUTPUT_ERROR);
        }

        // zapis statistik
        foreach($statArgs as $statArg)
        {
            if($statArg == 'loc')
            {
                fprintf($file, "$numOfInstructions\n");
            }
            elseif($statArg == 'comments')
            {
                fprintf($file, "$comments\n");
            }
            elseif($statArg == 'labels')
            {
                fprintf($file, "%d\n", count($labelArray));
            }
            else
            {
                fprintf($file, "$jumpRelated\n");
            }
        }

        fclose($file);
    }
}

// vypsani XML reprezentace na standardni vystup
echo $xmlDoc->saveXML();

exit(SUCCESS);


/**
 * Vrati radek kodu, odstrani komentare a prazdne radky, pri konci vstupu vraci hodnotu false.
 */
function getCodeLine()
{
    global $comments;

    // nacitani radku ze standardniho vstupu
    while($line = fgets(STDIN))
    {
        // preskakovani prazdnych radku
        if(preg_match('/^\s*$/', $line))
        {
            continue;
        }

        // preskakovani radku pouze s komentarem
        if(preg_match('/^\s*#.*/', $line))
        {
            $comments++;
            continue;
        }

        // odstraneni komentare za instrukci
        if(preg_match('/#.*/', $line))
        {
            $line = preg_replace('/#.*/', "", $line);
            $comments++;
        }

        $line = preg_replace('/^\s+/', "", $line);
        $line = preg_replace('/\s+$/', "", $line);

        return $line;
    }

    return false;
}


/**
 * Kontrola spravneho zapisu promenne.
 */
function checkVar($var)
{
    if(preg_match('/^(GF|LF|TF)@[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$/', $var))
    {
        return true;
    }

    return false;
}


/**
 * Kontrola spravneho zapisu navesti.
 */
function checkLabel($label)
{
    if(preg_match('/^[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$/', $label))
    {
        return true;
    }

    return false;
}


/**
 * Kontrola spravneho zapisu promenne a konstanty.
 * V pripade uspechu vrati typ konstanty, nebo informaci o tom, ze se jedna o promennou.
 * Jinak vraci false.
 */
function checkSymb($symb)
{
    if(checkVar($symb))
    {
        return 'var';
    }
    elseif(preg_match('/^nil@nil$/', $symb))
    {
        return 'nil';
    }
    elseif(preg_match('/^int@[+\-]?\d+$/', $symb))
    {
        return 'int';
    }
    elseif(preg_match('/^bool@(true|false)$/', $symb))
    {
        return 'bool';
    }
    elseif(preg_match('/^string@([^\s\\#]|(\\\d{3}))*$/', $symb))
    {
        return 'string';
    }
    else
    {
        return false;
    }
}


/**
 * Kontrola spravneho zapisu typu.
 */
function checkType($type)
{
    if(preg_match('/^(int|bool|string)$/', $type))
    {
        return true;
    }

    return false;
}


/**
 * Pokud je vstupem konstanta, je upravena pro zapis.
 */
function dealWithConst($word)
{
    return preg_replace('/^(nil|int|bool|string)@/', "", $word);
}


/**
 * Vytvoreni xml a nastaveni hlavicky.
 */
function createXML()
{
    $xmlDoc = new DOMDocument('1.0', 'UTF-8');
    $xmlDoc->formatOutput = true;

    return $xmlDoc;
}


/**
 * Nastaveni korene XML stromu.
 */
function setXMLRoot()
{
    global $xmlDoc;

    $xmlRoot = $xmlDoc->createElement('program');
    $xmlRoot->setAttribute('language', 'IPPcode20');
    $xmlRoot = $xmlDoc->appendChild($xmlRoot);

    return $xmlRoot;
}


/**
 * Pridani elementu funkce do vystupniho XML.
 */
function addXMLInstruction($order, $opcode)
{
    global $xmlDoc;
    global $xmlRoot;

    $xmlInstruction = $xmlDoc->createElement('instruction');
    $xmlInstruction->setAttribute('order', $order);
    $xmlInstruction->setAttribute('opcode', $opcode);
    $xmlInstruction = $xmlRoot->appendChild($xmlInstruction);

    return $xmlInstruction;
}


/**
 * Pridani argumentu k funkci do vystupniho XML.
 */
function addXMLArgument($xmlInstruction, $order, $type, $textElement)
{
    global $xmlDoc;

    $xmlArg = $xmlDoc->createElement("arg$order", $textElement);
    $xmlArg->setAttribute('type', $type);
    $xmlArg = $xmlInstruction->appendChild($xmlArg);
}

?>