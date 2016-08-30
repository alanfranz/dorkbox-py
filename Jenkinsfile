node {
    stage 'Build'
    catchError {
	checkout scm
	sh 'make clean test'
    } 

    stage 'Packaging'
    catchError {
	def distros = ["ubuntu-trusty", "ubuntu-xenial"]
	parallelize = [:]
	for (String distro: distros) {
	    parallelize[distro] = {
		sh "packaging/${distro}/build"
		}
	}
	parallel parallelize
    }


    step([$class: 'Mailer', notifyEveryUnstableBuild: false, sendToIndividuals: true])
}


