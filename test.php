<?php

/**
 * IPP - projekt 2
 * 
 * Dominik Nejedly (xnejed09)
 * 
 * Testovaci skript, ktery porovna ziskane vysledky s referencnimi.
 */

ini_set('display_errors', 'stderr');

// hodnoty nesouci informaci o vysledku testu, prvni z nich take vracena pri bezchybnem prubehu tohoto skiptu
const SUCCESS = 0;
const FAIL = 1;
const NOT_TESTED = 2;

// chybove navratove hodnoty
const PARAM_ERR = 10;
const INPUT_ERR = 11;
const OUTPUT_ERR = 12;

const INTERNAL_ERR = 99;

// zpracovani parametru
$getOpts = getopt("", array("help", "directory:", "recursive", "parse-script:", "int-script:", "parse-only", "int-only", "jexamxml:"));

// implicitni hodnoty pro zpusteni (vstupni argumenty je mohou zmenit)
$dir = ".";
$recursive = false;
$parScr = "parse.php";
$intScr = "interpret.py";
$parOnly = false;
$intOnly = false;
$jexamxml = "/pub/courses/ipp/jexamxml/jexamxml.jar";

// Pokud byly zadany argumenty, provede se jejich kontrola a nastaveni.
if($getOpts != false)
{
    if(array_key_exists("help", $getOpts))
    {
        if(count($getOpts) != 1)
        {
            errExit(PARAM_ERR, "Invalid combination of parameters!");
        }
        elseif(is_array($getOpts["help"]))
        {
            errExit(PARAM_ERR, "Multiple times parameter --help!");
        }

        echo "\nScript for automatic testing of succesive application parse.php and interpret.py.\n";
        echo "The script browses the specified directory with tests and uses these tests for automatic\n";
        echo "testing of the correct functionality of both previous programs, including generating of clear\n";
        echo "summary in HTML 5 to standard output.\n\n";
        echo "--help\t\t\tprint out help to standard output\n";
        echo "--directory=path\tsearching for tests in specified directory\n";
        echo "--recursive\t\tsearching for tests even in all subdirectories\n";
        echo "--parse-script=file\tfile with script in PHP 7.4 for analysis of source code in IPPcode20\n";
        echo "--int-script=file\tfile with script int python 3.8 for interpret of XML representation of code in IPPcode20\n";
        echo "--parse-only\t\tonly script for analysis of source code in IPPcode20 is tested\n";
        echo "--int-only\t\tonly script for interpret of XML representation of code in IPPcode20\n";
        echo "--jexamxml=file\t\tfile with JAR package with A7soft JExamXML tool\n\n";

        exit(SUCCESS);
    }

    if(array_key_exists("directory", $getOpts))
    {
        if(is_array($getOpts["directory"]))
        {
            $dir = checkParamArr($getOpts["directory"]);
        }
        else
        {
            $dir = $getOpts["directory"];
        }
    }

    if(array_key_exists("recursive", $getOpts))
    {
        $recursive = true;
    }

    if(array_key_exists("parse-script", $getOpts))
    {
        if(is_array($getOpts["parse-script"]))
        {
            $parScr = checkParamArr($getOpts["parse-script"]);
        }
        else
        {
            $parScr = $getOpts["parse-script"];
        }
    }

    if(array_key_exists("int-script", $getOpts))
    {
        if(is_array($getOpts["int-script"]))
        {
            $intScr = checkParamArr($getOpts["int-script"]);
        }
        else
        {
            $intScr = $getOpts["int-script"];
        }
    }

    if(array_key_exists("parse-only", $getOpts))
    {
        if(array_key_exists("int-only", $getOpts) || array_key_exists("int-script", $getOpts))
        {
            errExit(PARAM_ERR, "Invalid combination of parameters!");
        }

        $parOnly = true;
    }

    if(array_key_exists("int-only", $getOpts))
    {
        if(array_key_exists("parse-only", $getOpts) || array_key_exists("parse-script", $getOpts))
        {
            errExit(PARAM_ERR, "Invalid combination of parameters!");
        }

        $intOnly = true;
    }

    if(array_key_exists("jexamxml", $getOpts))
    {
        if(is_array($getOpts["jexamxml"]))
        {
            $jexamxml = checkParamArr($getOpts["jexamxml"]);
        }
        else
        {
            $jexamxml = $getOpts["jexamxml"];
        }
    }
}

// Kontrola, zda zadane vstupni soubory a adresar existuji.
if(!is_dir($dir))
{
    errExit(INPUT_ERR, "Directory does not exist!");
}

if(!$intOnly)
{
    if(!file_exists($parScr))
    {
        errExit(INPUT_ERR, "File with script in PHP does not exist!");
    }

    if(is_dir($parScr))
    {
        errExit(INPUT_ERR, "Parameter parse-script have to be file, not directory!");
    }
}

if(!$parOnly)
{
    if(!file_exists($intScr))
    {
        errExit(INPUT_ERR, "File with script in python does not exist!");
    }

    if(is_dir($intScr))
    {
        errExit(INPUT_ERR, "Parameter int-script have to be file, not directory!");
    }
}

if(!file_exists($jexamxml))
{
    errExit(INPUT_ERR, "File with JAR package with A7soft JExamXML tool does not exist!");
}

if(is_dir($jexamxml))
{
    errExit(INPUT_ERR, "Parameter jexamxml have to be file, not directory!");
}

// nacitani adresaru k prohledani a testovacich vstupnich souboru
$dir = preg_replace('/\/$/', "", $dir);

// zasobnik adresaru
$dirArr = array($dir);

// slovnik adresaru a testu v nich
$dirsAndSrcs = array();

// prohledavani adresaru
while(count($dirArr) > 0)
{
    // nacteni obsahu adresare a odstraneni aktualniho a rodicovkeho adresare
    $dirContent = array_diff(scandir($dirArr[0]), array(".", ".."));

    if($dirContent == false)
    {
        errExit(INTERNAL_ERR, "Scanning of directory failed!");
    }

    // [ole uchovavajici vstupni testovaci soubory
    $dirSrcs = array();

    // zpracovani obsahu adresare
    foreach($dirContent as $member)
    {
        // Pri rekuzrzivnim prohledavani uklada do zasobniku adresare k prohledani.
        if(is_dir($dirArr[0] . "/" . $member))
        {
            if($recursive)
            {
                array_push($dirArr, $dirArr[0] . "/" . $member);
            }
        }
        elseif(preg_match('/^.*\.src$/', $member))
        {
            $member = preg_replace('/\.src$/', "", $member);

            array_push($dirSrcs, $member);

            // pripadne dotvoreni souboru potrebnych k testu
            checkFile($dirArr[0], $member, "in");
            checkFile($dirArr[0], $member, "out");
            checkFile($dirArr[0], $member, "rc");
        }
    }

    // Pokud adresar obsahuje alespon jeden test, je ulozen ke zpracovani.
    if(count($dirSrcs) > 0)
    {
        $dirsAndSrcs[$dirArr[0]] = $dirSrcs;
    }

    array_shift($dirArr);
}

// pole s vysledky testu
$resultsArr = array();

// docasne soubory
$tmpFileOutParse = tempnam("./", "");
$tmpFileOutInt = tempnam("./", "");

// pruchod pres adresare ke zpracovani
foreach($dirsAndSrcs as $dir => $srcs)
{
    $srcArr = array();

    // pruchod pres jednotlive testy v danem adresari
    foreach($srcs as $src)
    {
        $retVal = 0;

        $rvArr = array();

        // Provede spusteni parseru v php, ulozi si navratovou hodnotu a vystup posle do docasneho souboru.
        if(!$intOnly)
        {
            exec("php7.4 " . $parScr . " < " . $dir . "/" . $src . ".src" . " > " . $tmpFileOutParse . " 2> /dev/null", $output, $retVal);
        }

        if(!$parOnly)
        {
            if($retVal == 0)
            {
                // nastaveni vstupniho souboru interpetu
                if($intOnly)
                {
                    $sourceFile = $dir . "/" . $src . ".src";
                }
                else
                {
                    $sourceFile = $tmpFileOutParse;
                }

                // spusteni interpretu nad urcitym testem, ulozeni navratove hodnoty do promenne a vystupu do docaskeho souboru
                exec("python3.8 " . $intScr . " --source=" . $sourceFile . " --input=" . $dir . "/" . $src . ".in" . " > " . $tmpFileOutInt . " 2> /dev/null", $output, $retVal);
            }
        }

        // Nacteni navratove hodnoty z testovaciho souboru s navratovym kodem
        $fdrc = fopen($dir . "/" . $src . ".rc", "r");

        if($fdrc == false)
        {
            unlink($tmpFileOutParse);
            unlink($tmpFileOutInt);
            errExit(INPUT_ERR, "Can not open file with return code!");
        }

        $rc = intval(fread($fdrc, filesize($dir . "/" . $src . ".rc")));

        fclose($fdrc);

        // porovnani modelove navratove hodnoty se ziskanou navratovou hodnotou, pripadne vysptupu a ulozeni vysledku
        if($rc == $retVal)
        {
            if($rc == 0)
            {
                // porovnani modeloveho vystupu se ziskanym
                if($parOnly)
                {
                    exec("java -jar " . $jexamxml . " " . $dir . "/" . $src . ".out" . " " . $tmpFileOutParse . " diffs.xml /D /pub/courses/ipp/jexamxml/options", $output, $status);

                    exec("rm -f diffs.xml");

                    if($status == 0)
                    {
                        $rvArr["out"] = SUCCESS;
                    }
                    else
                    {
                        $rvArr["out"] = FAIL;
                    }
                }
                else
                {
                    exec("diff " . $tmpFileOutInt . " " . $dir . "/" . $src . ".out > /dev/null", $output, $status);

                    if($status == 0)
                    {
                        $rvArr["out"] = SUCCESS;
                    }
                    else
                    {
                        $rvArr["out"] = FAIL;
                    }
                }
            }
            else
            {
                $rvArr["out"] = NOT_TESTED;
            }

            $rvArr["rc"] = SUCCESS;
        }
        else
        {
            $rvArr["rc"] = FAIL;
            $rvArr["out"] = NOT_TESTED;
        }

        $srcArr[$src] = $rvArr; 
    }

    // ulozeni vyslednych hodnot formou vnorenych slovniku (jmeno adresare odkazuje na pole testu a nazev testu na jeho vysledky)
    $resultsArr[$dir] = $srcArr;
}

// smazani docasnych souboru
unlink($tmpFileOutParse);
unlink($tmpFileOutInt);

// tvorba vysledneho html dokumentu
echo "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n\t<title>Test results</title>\n\t<meta charset=\"UTF-8\">\n\t<style>\n\thr.st1 {\n\t\tborder: 3px solid grey;\n\t}\n";

if(count($resultsArr) == 0)
{
    echo "\t</style>\n</head>\n<body>\n\t<h1>Test results</h1><hr class=\"st1\">\n\t<h3>No tests were found.</h3>\n";
}
else
{
    echo "\n\thr.st2 {\n\t\tborder: 1px solid grey;\n\t}\n";
    echo "\n\th3 {\n\t\tfont-size: 20px;\n\t}\n";
    echo "\n\tp.sz1 {\n\t\tfont-size: 17px;\n\t}\n";
    echo "\n\tp.sz2 {\n\t\tfont-size: 20px;\n\t}\n";
    echo "\n\thr.marg {\n\t\tmargin-top: 1.8em;\n\t}\n";
    echo "\n\ttable {\n\t\twidth: 100%;\n\t\tbackground-color: rgba(190, 190, 0, 0.1);\n\t}\n";
    echo "\n\ttable, th, td {\n\t\tborder: 1px solid black;\n\t\tborder-collapse: collapse;\n\t}\n";
    echo "\n\tth, td {\n\t\tpadding: 12px;\n\t\ttext-align: left;\n\t}\n";
    echo "\n\tth {\n\t\tfont-size: 20px;\n\t}\n";
    echo "\n\ttd {\n\t\tfont-size: 17px;\n\t}\n";
    echo "\n\t.Talign {\n\t\ttext-align: center;\n\t}\n";
    echo "\n\t.greenText {\n\t\tcolor: rgba(0, 255, 0, 1);\n\t}\n";
    echo "\n\t.redText {\n\t\tcolor: rgba(255, 0, 0, 1);\n\t}\n";
    echo "\n\t.greyText {\n\t\tcolor: grey;\n\t}\n";
    echo "\n\t.greenBack {\n\t\tbackground-color: rgba(0, 255, 0, 0.7);\n\t}\n";
    echo "\n\t.redBack {\n\t\tbackground-color: rgba(255, 0, 0, 0.7);\n\t}\n";
    echo "\n\t.col1 {\n\t\twidth: 28%;\n\t}\n";
    echo "\n\t.col2 {\n\t\twidth: 24%;\n\t}\n";
    echo "\n\t.col3 {\n\t\twidth: 24%;\n\t}\n";
    echo "\n\t.col4 {\n\t\twidth: 24%;\n\t}\n";
    echo "\t</style>\n</head>\n<body>\n\t<h1>Test results</h1><hr class=\"st1\">\n";

    // Ziskani ciselnych hodnot, aby mohly byt vypsany ve vrchni casti vyledneho dokumentu.
    $numOfAllTests = 0;
    $numOfAllSuccTests = 0;
    $numOfAllFailTests = 0;

    $succTestsInDirs = array();
    $failTestsInDirs = array();

    foreach($resultsArr as $dir => $tests)
    {
        $succTestsInDir = 0;
        $failTestsInDir = 0;

        foreach($tests as $test => $result)
        {
            $numOfAllTests++;

            if($result["rc"] == FAIL || $result["out"] == FAIL)
            {
                $numOfAllFailTests++;
                $failTestsInDir++;
            }
            else
            {
                $numOfAllSuccTests++;
                $succTestsInDir++;
            }
        }

        $succTestsInDirs[$dir] = $succTestsInDir;
        $failTestsInDirs[$dir] = $failTestsInDir;
    }

    if($numOfAllTests == $numOfAllSuccTests)
    {
        $colorOfAllTests = "greenText";
    }
    elseif($numOfAllTests == $numOfAllFailTests)
    {
        $colorOfAllTests = "redText";
    }
    else
    {
        $colorOfAllTests = "greyText";
    }

    echo "\t<h3>Number of all tests: <span class=\"$colorOfAllTests\">$numOfAllTests</h3>\n";
    printf("\t<p class=\"sz2\">Number of all successful tests: <span class=\"%s\"><b>%d</b></span></p>\n", ($numOfAllSuccTests > 0) ? "greenText" : "greyText", $numOfAllSuccTests);
    printf("\t<p class=\"sz2\">Number of all failed tests: <span class=\"%s\"><b>%d</b></span></p><hr class=\"st1\">\n", ($numOfAllFailTests > 0) ? "redText" : "greyText", $numOfAllFailTests);

    // Pro kazdy adresar vygeneruje tabulku s vysledky.
    foreach($resultsArr as $dir => $tests)
    {
        printf("\t<h3>Directory: <span class=\"%s\">%s</span></h3>\n", ($failTestsInDirs[$dir] > 0) ? "redText" : "greenText", $dir);
        printf("\t<p class=\"sz1\">Number of successful tests: <span class=\"%s\"><b>%d</b></span></p>\n", ($succTestsInDirs[$dir] > 0) ? "greenText" : "greyText", $succTestsInDirs[$dir]);
        printf("\t<p class=\"sz1\">Number of failed tests: <span class=\"%s\"><b>%d</b></span></p>\n", ($failTestsInDirs[$dir] > 0) ? "redText" : "greyText", $failTestsInDirs[$dir]);

        echo "\t<table>\n\t\t<col class=\"col1\">\n\t\t<col class=\"col2\">\n\t\t<col class=\"col3\">\n\t\t<col class=\"col3\">\n";
        echo "\t\t<tr>\n\t\t\t<th>Test</th>\n\t\t\t<th class=\"Talign\">Return code</th>\n\t\t\t<th class=\"Talign\">Output</th>\n\t\t\t<th class=\"Talign\">Summary</th>\n\t\t</tr>\n";

        // generovani jednotlivych radku s testy do tabulky
        foreach($tests as $test => $result)
        {
            $test = htmlspecialchars($test);

            if($result["rc"] == SUCCESS)
            {
                $rcColor = " greenBack";
                $rcState = "PASS";
            }
            else
            {
                $rcColor = " redBack";
                $rcState = "FAIL";
            }

            if($result["out"] == NOT_TESTED)
            {
                $outColor = "";
                $outState = "NOT TESTED";
            }
            elseif($result["out"] == SUCCESS)
            {
                $outColor = " greenBack";
                $outState = "PASS";
            }
            else
            {
                $outColor = " redBack";
                $outState = "FAIL";
            }

            if($result["rc"] == FAIL || $result["out"] == FAIL)
            {
                $sumColor = " redBack";
                $sumState = "FAILURE";
            }
            else
            {
                $sumColor = " greenBack";
                $sumState = "SUCCESS";
            }

            echo "\t\t<tr>\n\t\t\t<td>$test</td>\n\t\t\t<td class=\"Talign$rcColor\">$rcState</td>\n";
            echo "\t\t\t<td class=\"Talign$outColor\">$outState</td>\n\t\t\t<td class=\"Talign$sumColor\"><b>$sumState</b></td>\n\t\t<tr>\n";
        }

        echo "\t</table><hr class=\"st2 marg\">\n";
    }
}

echo "</body>\n</html>\n";

exit(SUCCESS);


/**
 * Pokud bylo zadano vice parametru stejneho typu, je provedena kontrola, zdali i jejich hodnoty jsou shodne.
 */
function checkParamArr($array)
{
    $firstMember = $array[0];

    array_shift($array);

    foreach($array as $member)
    {
        if($member != $firstMember)
        {
            errExit(PARAM_ERR, "Multiple times same parameters with different value!");
        }
    }

    return $firstMember;
}


/**
 * Chybove ukonceni skriptu a vypis chyboveho hlaseni
 */
function errExit($errCode, $errMessage)
{
    fprintf(STDERR, "$errMessage\n");
    exit($errCode);
}


/**
 * Kotrola existence ci pripadne dotvoreni souboru potrebneho k testu
 */
function checkFile($dir, $filename, $suffix)
{
    $path = $dir . "/" . $filename . "." . $suffix;

    if(!file_exists($path))
    {
        $fd = fopen($path, "w");

        if($fd == false)
        {
            errExit(INPUT_ERR, "Input file was not created!");
        }

        if($suffix == "rc")
        {
            fprintf($fd, "0");
        }

        fclose($fd);
    }
}

?>