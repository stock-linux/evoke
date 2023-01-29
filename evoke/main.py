"""Evoke.

Usage:
  evoke create <name> <version> <description> <source> [<maintainer>] [<license>] [<url>]
  evoke create_blfs <blfs_link> <description> [<maintainer>] [<license>] [<url>]
  evoke increment
  evoke build

Options:
    create <name> <version> <description> <source> [<maintainer>] [<license>] [<url>]  Create a new package
    create_blfs <blfs_link> <description> [<maintainer>] [<license>] [<url>] Create a new package with autofil. Works only with BLFS website.
    -h --help                                      Show this screen.

"""

import shutil
from docopt import docopt
import os, colorama, requests, magic, re
import subprocess as sp
from bs4 import BeautifulSoup

from elftools.elf.elffile import ELFFile, DynamicSection

def read_elf_deps(elffile):
    deps = []
    for section in elffile.iter_sections():
        if not isinstance(section, DynamicSection):
            continue

        for tag in section.iter_tags():
            if tag.entry.d_tag == 'DT_NEEDED':
                deps.append(tag.needed)

    return deps

def check_output(out: int):
    if out != 0:
        print(colorama.Fore.RED + 'Error: ' + str(out) + colorama.Fore.RESET)
        exit(1)


def get_html(url):
    """
    Get the raw HTML file of the given URL
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(requests.get(url).text)
        f.close()


def get_dependencies():
    """
    Get packages name and version of the dependencies
    """    
    dependencies = []
    packages = {}
    
    with open("index.html") as f:
        soup = BeautifulSoup(f, 'html.parser')
        tag = soup.find_all(class_="required")
        tag += soup.find_all(class_="recommended")
        tags = (tag[0].find_all("a", class_="xref") + tag[1].find_all("a", class_="xref")) 

        for tag in tags:
            dependencies += [tag.get("title")]

        for dependency in dependencies:
            separator = dependency.rindex('-')
            dependency[:separator].replace(' ','-')
            version = dependency[separator + 1:]
            packages.update({package_name.lower() : version})

        f.close()
    return packages


def get_build_info():
    """
    Get source link, MD5 sum, download size, disk space required and SBU of the package.
    
    TODO: test getting package name and version.
    """
    with open("index.html") as f:
        soup = BeautifulSoup(f, 'html.parser')
        itemlist = soup.find(class_="itemizedlist")
        listitems = itemlist.find_all(class_="listitem")
        
        for i in range(6):
            listitem = listitems[i]
            match i:
                case 0:
                    package_source_link = listitem.find("p").find("a").get("href")
                case 2:
                    package_sum = listitem.find("p").get_text().strip()[18:]
                case 3:
                    package_download_size = listitem.find("p").get_text().strip()[15:]
                case 4:
                    package_disk_size = listitem.find("p").get_text().strip()[31:].split(" ", 2)
                    if len(package_disk_size) == 2:
                        package_disk_size = " ".join(package_disk_size)
                    else:
                        package_disk_size = " ".join(package_disk_size[:-1])
                case 5:
                    package_sbu = listitem.find("p").get_text().strip()[22:][:3]
         
        title = soup.find("title").get_text().strip()
        separator = title.rindex('-')
        package_name = title[:separator].replace(' ','-')
        package_version = title[separator + 1:]

        package_class = soup.find(class_="package")
        description_raw = package_class.find("p")
        package_description = ' '.join(description_raw.get_text().strip().split())

        f.close()
    return [package_name, package_version, package_source_link, package_sum, package_download_size, package_disk_size, package_sum, package_description]


if __name__ == '__main__':
    arguments = docopt(__doc__)
    
    if arguments['create_blfs']:
        get_html(arguments['<blfs_link>']) # To test
        dependencies = get_dependencies()
        package_name, package_version, package_source_link, package_sum, package_download_size, package_disk_size, package_sum, package_description = get_build_info()

        os.makedirs(package_name)
        os.chdir(package_name)
        os.makedirs('metadata')
        os.makedirs('data')
        os.makedirs('scripts')

        with open('metadata/PKGINFO', 'w') as f:
            # PKGINFO is formatted like this:
            # field (in lower case) = value
            f.write('name = ' + package_name + '\n')
            f.write('version = ' + package_version + '\n')
            f.write('pkgrel = 1' + '\n')
            f.write(f"description = {package_description}" + '\n')
            f.write('source = ' + package_source_link.replace(package_name, "$name").replace(package_version, "$version") + '\n')
            f.write(f"makedepends = ({' '.join(dependencies.keys())})" + '\n')

            # Add optional fields
            if arguments['<maintainer>'] != None:
                f.write('maintainer = ' + arguments['<maintainer>'] + '\n')
            if arguments['<license>'] != None:
                f.write('license = ' + arguments['<license>'] + '\n')
            if arguments['<url>'] != None:
                f.write('url = ' + arguments['<url>'] + '\n')

        # Log the creation of the package
        print(colorama.Fore.GREEN + 'Created package ' + package_name + ' version ' + package_version + colorama.Fore.RESET)


    if arguments['create']:
        os.makedirs(arguments['<name>'])
        os.chdir(arguments['<name>'])
        os.makedirs('metadata')
        os.makedirs('data')
        os.makedirs('scripts')

        with open('metadata/PKGINFO', 'w') as f:
            # PKGINFO is formatted like this:
            # field (in lower case) = value
            f.write('name = ' + arguments['<name>'] + '\n')
            f.write('version = ' + arguments['<version>'] + '\n')
            f.write('pkgrel = 1' + '\n')
            f.write('description = ' + arguments['<description>'] + '\n')
            f.write('source = ' + arguments['<source>'].replace(arguments['<name>'], "$name").replace(arguments['<version>'], "$version") + '\n')
            
            # Add optional fields
            if arguments['<maintainer>'] != None:
                f.write('maintainer = ' + arguments['<maintainer>'] + '\n')
            if arguments['<license>'] != None:
                f.write('license = ' + arguments['<license>'] + '\n')
            if arguments['<url>'] != None:
                f.write('url = ' + arguments['<url>'] + '\n')

        # Log the creation of the package
        print(colorama.Fore.GREEN + 'Created package ' + arguments['<name>'] + ' version ' + arguments['<version>'] + colorama.Fore.RESET)


    if arguments['build']:
        if os.path.exists('build.stderr.log'):
            os.remove('build.stderr.log')
        if os.path.exists('build.stdout.log'):
            os.remove('build.stdout.log')
        # Build the package
        print(colorama.Fore.CYAN + 'Building package...' + colorama.Fore.RESET)
    
        # Create temp build directory
        if os.path.exists('build'):
            shutil.rmtree('build')
            
        os.makedirs('build')
        os.chdir('build')
        os.makedirs('work')

        # Download source
        # Note: source is read from the PKGINFO file
        # At the same time, we get the name and version of the package
        print(colorama.Fore.CYAN + 'Downloading source...' + colorama.Fore.RESET)

        name = ""
        version = ""
        source = ""
        makedepends_str = ""
        run_depends_str = ""
        run_deps = []

        with open('../metadata/PKGINFO', 'r') as f:
            for line in f:
                if line.startswith('name'):
                    name = line.split(' = ')[1].strip()
                elif line.startswith('version'):
                    version = line.split(' = ')[1].strip()
                elif line.startswith('source'):
                    source = line.split(' = ')[1].strip()
                elif line.startswith('makedepends'):
                    makedepends_str = line.split(' = ')[1].strip()
                elif line.startswith('run'):
                    run_depends_str = line.split(' = ')[1].strip()

        sources = []
        if source.startswith('(') and source.endswith(')'):
            split = source.replace('(', '').replace(')', '').split(' ')
            for s in split:
                sources.append(s.replace("$name", name).replace("$version", version))
        else:
            sources.append(source.replace("$name", name).replace("$version", version))

        for s in sources:
            r = requests.get(s)
            with open(s.split('/')[-1], 'wb') as f:
                f.write(r.content)
        
        makedepends = []
        if makedepends_str.startswith('(') and makedepends_str.endswith(')'):
            split = makedepends_str.replace('(', '').replace(')', '').split(' ')
            for s in split:
                makedepends.append(s.strip())
        else:
            makedepends.append(makedepends_str.strip())
        
        if run_depends_str.startswith('(') and run_depends_str.endswith(')'):
            split = run_depends_str.replace('(', '').replace(')', '').split(' ')
            for s in split:
                run_deps.append(s.strip())
        else:
            if run_depends_str != '':
                run_deps.append(run_depends_str.strip())

        # Log a successful download
        print(colorama.Fore.GREEN + 'Downloaded source' + colorama.Fore.RESET)
        
        # Install makedepends
        print(colorama.Fore.CYAN + 'Installing makedepends...' + colorama.Fore.RESET)
        for m in makedepends:
            print(colorama.Fore.CYAN + 'Installing ' + m + '...' + colorama.Fore.RESET)
            os.system('evox get ' + m)

        # Install makedepends
        print(colorama.Fore.CYAN + 'Installing makedepends...' + colorama.Fore.RESET)
        for m in makedepends:
            print(colorama.Fore.CYAN + 'Installing ' + m + '...' + colorama.Fore.RESET)
            os.system('evox get ' + m)

        # Set the environment variable EVOKE_BUILD_DIR to the build directory
        os.environ['EVOKE_BUILD_DIR'] = os.getcwd()
        os.environ['SRC'] = os.getcwd()
        # Set the environment variable EVOKE_WORK_DIR to the work directory
        os.environ['EVOKE_WORK_DIR'] = os.getcwd() + '/work'
        # Set the environment variable PKG to the data directory
        os.environ['PKG'] = os.path.abspath('../data')
        os.environ['EVOKE_PKG_DIR'] = os.path.abspath('../data')
        # Set the environment variable name to the name of the package
        os.environ['name'] = name
        # Set the environment variable version to the version of the package
        os.environ['version'] = version

        # Set the variables MAKEFLAGS and NINJAJOBS to the JOBS environment variable
        # Note that this is only done if the JOBS environment variable is set
        if 'JOBS' in os.environ:
            os.environ['MAKEFLAGS'] = '-j' + os.environ['JOBS']
            os.environ['NINJAJOBS'] = os.environ['JOBS']

        # Change to the work directory
        os.chdir('work')

        # Run the build script
        print(colorama.Fore.CYAN + 'Running build script...' + colorama.Fore.RESET)
        
        ret = sp.run("bash ../../scripts/PKGBUILD", capture_output=True, shell=True)

        # Log build results
        build_log_file = open("../../build.stdout.log", "w")
        build_log_file.write(ret.stdout.decode())
        build_log_file.close()

        err_log_file = open("../../build.stderr.log", "w")
        err_log_file.write(ret.stderr.decode())
        err_log_file.close()

        try:
            ret.check_returncode()
            # Log a successful build
            print(colorama.Fore.GREEN + 'Built package' + colorama.Fore.RESET)
        except sp.CalledProcessError:
            print(colorama.Fore.RED + 'Error: Build failed' + colorama.Fore.RESET)
            exit(1)

        # Generate the package tree
        print(colorama.Fore.CYAN + 'Generating package tree...' + colorama.Fore.RESET)
        # Change to the data directory
        os.chdir('../../data')
        os.system('find > ../metadata/PKGTREE')
        shutil.rmtree('../build')
        # Log a successful package tree generation
        print(colorama.Fore.GREEN + 'Generated package tree' + colorama.Fore.RESET)

        # We must detect the runtime dependencies of the package
        # We do this by checking each ELF file in the package tree
        # If the file is an ELF file, we check if it has any dependencies
        # If it does, we add them to the PKGDEPS file
        print(colorama.Fore.CYAN + 'Detecting runtime dependencies...' + colorama.Fore.RESET)
                # Get the future run dependencies by checking ELF files of the package
        global_elfdeps = []
        for subdir, dirs, files in os.walk("."):
            for file in files:
                try:
                    if not magic.from_file(os.path.join(subdir, file)).startswith("ELF"):
                        continue
                    if re.search("^ELF.*executable.*not stripped", magic.from_file(os.path.join(subdir, file))):
                        os.system("strip --strip-all " + os.path.join(subdir, file))
                    elif re.search("^ELF.*shared object.*not stripped", magic.from_file(os.path.join(subdir, file))):
                        os.system("strip --strip-unneeded " + os.path.join(subdir, file))
                    elif re.search("current ar archive", magic.from_file(os.path.join(subdir, file))):
                        os.system("strip --strip-debug " + os.path.join(subdir, file))
            
                    elffile = ELFFile(open(os.path.join(subdir, file), "rb"))
                    elfdeps = read_elf_deps(elffile)
                    global_elfdeps.extend(elfdeps)
                except:
                    continue

        global_elfdeps = list(dict.fromkeys(global_elfdeps))

        for dep in global_elfdeps:
            for pkg in os.listdir("/var/evox/packages"):
                if pkg == "DB":
                    continue
                for line in open("/var/evox/packages/" + pkg + "/PKGTREE", "r").readlines():
                    if line.split("/")[-1].strip() == dep:
                        if not pkg in run_deps:
                            run_deps.append(pkg)

        # Write the run dependencies to the PKGDEPS file
        with open('../metadata/PKGDEPS', 'w') as f:
            for dep in run_deps:
                if dep != name:
                    f.write(dep + '\n')

        # Log a successful detection of runtime dependencies
        print(colorama.Fore.GREEN + 'Detected runtime dependencies' + colorama.Fore.RESET)


        # Check if the PKGTREE line count is greater than 1
        with open('../metadata/PKGTREE', 'r') as f:
            if len(f.readlines()) <= 1:
                print(colorama.Fore.RED + 'Error: PKGTREE is empty' + colorama.Fore.RESET)
                exit(1)

        # Generate the package
        print(colorama.Fore.CYAN + 'Generating package...' + colorama.Fore.RESET)
        os.chdir('../..')
        os.system('tar -cJpf ' + name + '-' + version + '.tar.xz ' + name)
        # Change .tar.xz to .evx
        os.rename(name + '-' + version + '.tar.xz', name + '-' + version + '.evx')
        # Log a successful package generation
        print(colorama.Fore.GREEN + 'Generated package' + colorama.Fore.RESET)


    if arguments['increment']:
        # Increment the package release
        print(colorama.Fore.CYAN + 'Incrementing package release...' + colorama.Fore.RESET)
        with open('metadata/PKGINFO', 'r') as f:
            lines = f.readlines()

        with open('metadata/PKGINFO', 'w') as f:
            for line in lines:
                if line.startswith('pkgrel'):
                    pkgrel = int(line.split(' = ')[1].strip())
                    pkgrel += 1
                    f.write('pkgrel = ' + str(pkgrel) + '\n')
                else:
                    f.write(line)

        # Log a successful increment
        print(colorama.Fore.GREEN + 'Incremented package release' + colorama.Fore.RESET)
