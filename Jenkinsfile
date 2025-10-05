pipeline {
  agent any
  environment {
  IMAGE_NAME = "multi-platform-downloader"
  REGISTRY = "docker.io"  // Or leave empty; creds inject USR/PSW
}
  }
  options {
    timestamps()
    ansiColor('xterm')
    buildDiscarder(logRotator(numToKeepStr: '15'))
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    stage('Set up Python') {
      steps {
        bat '''
          python -m venv venv
          venv\\Scripts\\activate
          pip install --upgrade pip
          pip install -r requirements.txt
          '''
      }
    }
    stage('Lint') {
      steps {
        sh '''
        . venv/bin/activate
        pip install ruff
        ruff check . || true
        '''
      }
    }
    stage('Unit Tests') {
      when { expression { fileExists('tests') } }
      steps {
        sh '''
        . venv/bin/activate
        pip install pytest
        pytest -q || true
        '''
      }
    }
    stage('Build Image') {
      steps {
        script {
          def tag = "${env.BUILD_NUMBER}".trim()
          sh "docker build -t ${IMAGE_NAME}:${tag} ."
        }
      }
    }
    stage('Smoke Test Container') {
      steps {
        script {
          def tag = "${env.BUILD_NUMBER}".trim()
          sh '''
          set -e
          docker run -d --name mpd_test -p 18080:8000 ${IMAGE_NAME}:''' + tag + '''
          echo 'Waiting for app...'
          for i in $(seq 1 20); do
            if curl -fsS http://localhost:18080/ >/dev/null 2>&1; then echo 'App up'; break; fi
            sleep 1
          done
          curl -f http://localhost:18080/ | head -n 5
          docker logs mpd_test | tail -n 30
          docker rm -f mpd_test
          '''
        }
      }
    }
    stage('Push Image') {
      when { expression { env.REGISTRY_USR != null } }, value: '' , not { environment name: 'REGISTRY', value: '' } } }
      steps {
        script {
          def tag = "${env.BUILD_NUMBER}".trim()
          sh "docker tag ${IMAGE_NAME}:${tag} $REGISTRY_USR/${IMAGE_NAME}:${tag}"
          sh "docker login -u $REGISTRY_USR -p $REGISTRY_PSW"
          sh "docker push $REGISTRY_USR/${IMAGE_NAME}:${tag}"
        }
      }
    }
  }
  post {
    always {
      sh 'docker system prune -f || true'
      archiveArtifacts artifacts: 'Dockerfile', fingerprint: true
    }
  }
}
