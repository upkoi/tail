# Installing Python 3 and Docker on OS X
The core prerequisites for TAIL on OSX are python 3 (3.6 is strongly recommended) and docker. Try this guide if you're missing one or both of those.

## Check and Install Homebrew
We'll use [Homebrew](https://brew.sh/), a package manager for OS X, to install Python as well as Docker. Install Homebrew by running the following in a terminal:

```
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

Once Homebrew is installed proceed to the next steps.

## Check and Install Python 3
Install Python 3 using:

```
brew install python3
```

Verify the installation afterwards using:

```
python3 -V
```

Your output should look similar to:

_Python 3.6.7_

## Install Docker
Install docker using:

```
brew cask install docker
```

Verify your installation by running the _hello-world_ container:

```
docker run hello-world
```
