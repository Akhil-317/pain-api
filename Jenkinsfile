pipeline {
    agent { label 'Jenkins_Slave_node' }

    parameters {
        string(name: 'BRANCH', defaultValue: 'main', description: 'Git branch to build from')
    }

    environment {
        REPO_URL = 'https://rajsunkara@dev.azure.com/rajsunkara/Integrated%20Payable/_git/Integrated%20Payable'
        CREDENTIALS_ID = 'Jenkins-Pipeline-Ip-Agent'
        IMAGE_NAME = 'pain001-api'
        CONTAINER_NAME = 'pain001-api-container'
        PORT = '8000'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: "${params.BRANCH}", credentialsId: "${CREDENTIALS_ID}", url: "${REPO_URL}"
            }
        }

        stage('Clean Old Container') {
            steps {
                sh """
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME} || true
                    docker rmi -f ${IMAGE_NAME}:latest || true
                """
            }
        }


        stage('Debug Environment') {
            steps {
                sh 'echo "Current PWD:" && pwd'
                sh 'ls -la'
                sh 'env'
            }
        }


        stage('Build Image') 
        {
            steps 
            {
                dir("${env.WORKSPACE}") 
                {
                sh 'ls -la'  // optional: confirm files are there
                sh 'docker build --no-cache -t ${IMAGE_NAME}:latest .'
                }
            }
        }

        stage('Run Container') {
            steps {
                sh """
                    docker run --env-file .env \
                    -v \$(pwd)/ca-certificate.crt:/app/ca-certificate.crt \
                    -d -p ${PORT}:${PORT} --name ${CONTAINER_NAME} ${IMAGE_NAME}:latest
                """
            }
        }
    }

    post {
        failure {
            echo '❌ Build or deployment failed.'
        }
        success {
            echo '✅ Deployment successful.'
        }
    }
}
