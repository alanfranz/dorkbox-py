stage 'Build'
node {
    catchError {
	checkout scm
	sh 'make clean test'
    } 
    step([$class: 'Mailer', notifyEveryUnstableBuild: false, sendToIndividuals: true])
}
