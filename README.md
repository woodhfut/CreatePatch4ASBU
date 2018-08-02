# CreatePatch4ASBU
This script automate the process of creating test fix patches of ASBU, which is pretty time consuming. 
what it will do: 

    a. upload binaries to sign website and download them after binaries get signed. 

    b. help create .caz file for createpatch.exe

    c. set system env vairable CA_APM for corresponding ASBU version automatically

    d. call createpatch.exe to create the patch binary(e.g.T00009527.exe)

    e. upload patch binary(e.g.T00009527.exe) to sign website and download it after get signed.


NOTE: This works only in Arcserve internal env, since it need connect to internal web to do the sign binaries work. 


prequisitions:
    1. you need copy APM to the same folder as the CreatePatchMT.py, and set the relative path accordingly in the file

    2. You also need a folder in the same directory with exact name of the fix (e.g. T00009527) containing the binaries included in the fix, also T00009527.txt for createpatch.exe to use. 

usage:
python CreatePatchMT.py T00009527 17.5.1

    T00009527: the fix name created in l2fix. 
    17.5.1 : The ASBU version of the fix applied to.