# tr4v31_b0t

# Docker
Build the Docker image: Open a terminal or command prompt, navigate to your project directory, and run the following command to build the Docker image:

    docker build -t tr4v31_b0t .

This command tells Docker to build an image using the Dockerfile in the current directory and tag it with the name "my-python-app" (you can change this to your preferred name).

Once the image is built, you can run it in a container using the following command:

    docker run -it --rm tr4v31_b0t

This command starts a new Docker container based on the image you built. The -it option enables an interactive session within the container, and --rm removes the container automatically after it exits.

    docker run --name tr4v31_b0t tr4v31_b0t
