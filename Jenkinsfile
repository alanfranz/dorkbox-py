node {
    stage 'Build'
    catchError {
	checkout scm
	sh 'make clean test'
    } 

    stage 'Packaging'
    catchError {
	sh 'packaging/ubuntu-trusty/build'
	sh 'packaging/ubuntu-xenial/build'
    }

    step([$class: 'Mailer', notifyEveryUnstableBuild: false, sendToIndividuals: true])
}


