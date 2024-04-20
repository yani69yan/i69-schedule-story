pipeline {
    agent { label 'master'  }

    parameters {
        string(defaultValue: 'production', description: 'enter the branch name to deploy', name: 'branch')
        string(description: 'enter the rev_ver', name: 'REV_VER')
    }

    stages {
        stage('Prepare environment'){
          steps {
                script {
                    env.BRANCH_PARAM_COPY = "${branch}"
                    env.REV_VER_PARAM_COPY = "${REV_VER}"
                }
            }
    }
        stage("Backup code") {
        steps {
            script {
                // Save the current branch and commit hash
                def branch = params.branch
                def commit = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()

                // Connect to the server and backup the code
                withCredentials([usernamePassword(credentialsId: 'robot-server-login', usernameVariable: 'SSH_USERNAME', passwordVariable: 'SSH_PASSWORD')]) {
                    sh """
                        sshpass -p $SSH_PASSWORD ssh -o StrictHostKeyChecking=no $SSH_USERNAME@176.9.62.19 -p 2290 '
                        cd /mnt &&
                        rm -rf /mnt/backups/i69-apibackup.tar.gz &&
                        tar -czvf /mnt/backups/i69-apibackup.tar.gz --exclude='i69-api/host.access.log' i69-api
                        '
                    """
                }
            }
        }
    }

        stage("Deploy code to main server") {
            steps {
                script {
                    // Save the current branch and commit hash
                    def branchs = params.branch
                    def rev_ver = params.branch

                    // Connect to the server and deploy the code
                    withCredentials([usernamePassword(credentialsId: 'robot-server-login', usernameVariable: 'SSH_USERNAME', passwordVariable: 'SSH_PASSWORD')]) {
                        sh """
                            sshpass -p $SSH_PASSWORD ssh -o StrictHostKeyChecking=no $SSH_USERNAME@176.9.62.19 -p 2290 '
                            echo "${REV_VER}"
                            echo "${params.REV_VER}"
                            cd /mnt &&
                            cd i69-api &&
                            git remote set-url origin git@gitlab.i69app.com:dev-center/i69-api.git &&
                            git config --global pull.ff false &&
                            git config --global pull.rebase true &&
                            git fetch && git pull &&
                            git checkout ${params.branch} &&
                            git reset --hard ${params.REV_VER} &&
                            docker-compose -f docker-compose.prod.yml build &&
                            docker-compose -f docker-compose.prod.yml up -d --remove-orphans
                            '
                        """
                    }
                }
            }
        }


    }

    post {
        always{
             cleanWs()
        }
    }
}
