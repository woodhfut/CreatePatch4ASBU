import os
import subprocess
import shutil
import requests
from bs4 import BeautifulSoup
from requests_ntlm import HttpNtlmAuth
from multiprocessing.pool import ThreadPool
import sys
import argparse

apm_version_path = {
    '16.5.1' : r'APM\APMr16.5sp1\build7003',
    '17.0' : r'APM\APMr17\build7067',
    '17.5' : r'APM\APMr17.5\build7861',
    '17.5.1' : r'APM\APMr17.5SP1\build7903',
    '18.0': r'APM\APMr18\APMr18\build8001',
}

url = 'http://rmdm-bldvm-l901:8000/sign4dev.aspx'
account = 'qiang.liu@arcserve.com'
password ='<PASSWORD>'


def createFix(fixname):    
    print('Start creating fix {}'.format(fixname))

    fixpath =  fixname
    results = []

    if os.path.exists(fixpath):   
        files = []
        for (dirpath, _, filenames) in os.walk(fixpath):
            for f in filenames:
                files.append(os.path.join(dirpath,f))
            break
        if any(f.lower().endswith(fixname.lower() + '.txt') for f in files) :
            print('{} exists, good to go.'.format(fixname + '.txt'))
        else:
            print('{} is not included, exit!'.format(fixname + '.txt'))
            exit()
        
        pool = ThreadPool(processes=len(files))
        for f in files:
            if(not f.lower().endswith(fixname.lower() + '.exe') and not f.lower().endswith('.txt')):
                print('trying to sign file '+f)
                ar = pool.apply_async(signBinary,(f,))
                results.append(ar)
        pool.close()
        pool.join()
    else:
        print('fix path {} doesnot exists...\nexit..'.format(fixpath))
        exit()
    
    if all([x.get()[1] for x in results]):
        print('sign all binaries successfully.')
        print('Start create .caz file.')
        cazname = fixname + '.caz'
        cmd = '{} -w {}'.format(cazipxp, ' '.join(filter(lambda x : not x.lower().endswith(fixname.lower() + '.exe'),files)) + ' '  + cazname)
        print(cmd)
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as ex:
            print('Error create .caz file, exit.')
            exit()

        if os.path.isfile(cazname):
            print('caz created successfully...')
        else:
            print('failed to create caz file, exit.')
            exit()

        print('copy {} to apm folder {}'.format(cazname, apm))
        shutil.move(cazname, os.path.join(apm, cazname))

        if os.path.exists(os.path.join(apm,fixname)):
            shutil.rmtree(os.path.join(apm, fixname))

        print('start create {}.exe'.format(fixname))
        cmd = '{} -p {} {}'.format(createpatch, os.path.join(apm,cazname), fixname)
        #needed by createpatch.exe, which need CA_APM be set in system vairable, this will require administrator previlege.
        subprocess.run('setx CA_APM {} /M'.format(apm))
        print(cmd)
        subprocess.run(cmd)

        exepath = os.path.join(apm,fixname+'\\MQA\\Build.000\\'+fixname+'.exe')
        if os.path.isfile(exepath):
            print('.exe file created successfully.')
            shutil.copy(exepath, fixpath + '\\' + fixname+'.exe')
            signBinary(fixpath + '\\' + fixname+'.exe')

            print('all good....')
        else:
            print('failed to create the exe file, exit.')
            exit()
    else:
        for ar in results:
            r = ar.get()
            if not r[1]:
                print('problem during sign binary{}... '.format(r[0]))
        print('quit the create patch process.')
        exit()


def signBinary(bin):
    #bin is like T00009527\ntagent.dll.2003.2008.2008R2
    result = False
    binname_ext = bin.split('\\')[1]
    names = binname_ext.split('.')
    binname = names[0] + '.' + names[1]
    temp_folder = bin.replace('\\','_')
    
    print('copy and rename binary {}.'.format(bin))
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    binname_dst = os.path.join(temp_folder, binname)
    shutil.copy(bin,binname_dst)

    print('start signing file {}'.format(bin))
    headers = {
        #'Host': 'rmdm-bldvm-l901:8000',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
    }
    s = requests.Session()
    s.auth =HttpNtlmAuth(account,password)
    r = s.get(url,headers = headers )
    print('get status code for {} is {}'.format(bin, r.status_code))
    if r.status_code == 200:
        soup =  BeautifulSoup(r.text,'html.parser')

        vs = soup.find(id='__VIEWSTATE')['value']
        ev = soup.find(id='__EVENTVALIDATION')['value']
        with open(binname_dst,'rb') as f:
            files = {'FileUpload1': f,}
            data = {
                '__VIEWSTATE': vs,
                '__EVENTVALIDATION':ev,       
                'Button1':'Upload File',
            }
            r = s.post(url,files = files, data=data)
        print(r.status_code)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a',text='Download')
            print('links:{}'.format(links))
            if links and len(links) > 0:
                link = links[0].get('href')
                #sometimes the link is incorrect due to extra space before port number. 
                link = link.replace(': ',':')
                print(link)

                with s.get(link, headers=headers, stream=True) as r:
                #name = bin.split('\\')[-1]
                    with open(binname_dst,'wb') as f:
                        for chunk in r.iter_content():
                            f.write(chunk)
                result = True
                #r.close()
            else:
                print('failed to get the download link for signed binary {}.'.format(bin))
                print(r.text)
                #exit()
                shutil.rmtree(temp_folder)
                return (temp_folder, result)

            print('move signed binary back to fix path {}'.format(bin))
            shutil.move(binname_dst, bin)
            shutil.rmtree(temp_folder)
        else:
            print('failed to post data, ret={}'.format(r.status_code))
    else:
        print('failed to get from {}, ret ={}'.format(url, r.status_code))
    return (temp_folder, result)

if __name__ == '__main__':
    '''
    usage:
        python CreatePatchMT.py <fixname> <fixversion>
        fixname: e.g. T00009527
        fixversion: 
            16.5.1
            17.0
            17.5.1
            18.0
    example:
        python CreatePatchMT.py T00009527 17.5.1
    '''
    parser =  argparse.ArgumentParser(description='Create fix for asbu.', usage='Python %(prog)s fixname fixversion')
    parser.add_argument('fixname',  help='the fix name. e.g. T00009527')
    parser.add_argument('fixversion',  help='the fix version. e.g. 17.5.1 OR 18.0')
    args = parser.parse_args()

    apm =  os.path.join(os.path.dirname(os.path.abspath(__file__)), apm_version_path[args.fixversion])
    cazipxp = os.path.join(apm, 'cazipxp.exe')
    createpatch = os.path.join(apm, 'CreatePatch.exe')
    createFix(args.fixname)
    #signBinary('T00001201\\ntagent.dll.2003.2008.2008R2')