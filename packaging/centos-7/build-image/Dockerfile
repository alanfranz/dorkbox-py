FROM alanfranz/fwd-centos-7:latest
MAINTAINER Alan Franzoni <username@franzoni.eu>
# whatever is required for building should be installed in this image; just like BuildRequires: for RPM specs
RUN yum -y install epel-release rsync which 
RUN yum -y install python34 python34-devel python34-setuptools
RUN easy_install-3.4 "virtualenv==15.0.3"
