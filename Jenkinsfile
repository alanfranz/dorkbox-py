node {
    stage 'Build'
    catchError {
	checkout scm
	sh 'make clean test'
    } 

    stage 'Packaging'
	def distros = ["ubuntu-trusty", "ubuntu-xenial", "debian-jessie", "fedora-24", "centos-7"]
	parallelize = [:]
	for (String distro: distros) {
	    parallelize[distro] = {
		catchError {
			println "PACKAGING START ${distro}"
			sh "packaging/${distro}/build"
			println "PACKAGING END ${distro}"
			}
		}
	}
	parallel parallelize


    step([$class: 'Mailer', notifyEveryUnstableBuild: false, sendToIndividuals: true])
}


