node {
    stage 'Build'
    catchError {
//	git url: 'git@github.com:alanfranz/foolscrate.git', branch: 'v1dev'
	checkout scm
	sh 'make clean test'
    } 

	def distros = ["ubuntu-trusty", "ubuntu-xenial", "debian-jessie", "fedora-24", "centos-7"]
//	parallelize = [:]
	for (String distro: distros) {

    	stage "Packaging ${distro}"
		catchError {
			println "PACKAGING START ${distro}"
			sh "packaging/${distro}/build"
			println "PACKAGING END ${distro}"
			}
	}
//	parallel parallelize


    step([$class: 'Mailer', notifyEveryUnstableBuild: true, sendToIndividuals: true, recipients: 'username@franzoni.eu'])
}


