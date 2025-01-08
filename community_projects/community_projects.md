# How to Add a Community Project

This guide will walk you through creating and structuring your community project in the repository.

---

## 1. Run the Basic Pipeline

Ensure your environment is set up properly by following the repository instructions and successfully running the basic pipelines. This step verifies your setup.

---

## 2. Review the Basic Pipelines Documentation

Familiarize yourself with the basic pipeline by reading the documentation [here](../doc/basic-pipelines.md).

---

## 3. Create Your Project Directory

Navigate to the `community_projects` folder and create a directory for your project:

```bash
cd community_projects
mkdir <your_project_name>
cd <your_project_name>
```

---

## 4. Copy the Template Example

Copy the contents of the template example to your project directory:

```bash
cp ../template_example/* .
```

---

# Using Basic Pipelines as a Template

The following sections explain how to build your project based on the existing basic pipelines.

---

## Modify the Callback Class

1. Update the callback class, which inherits from `app_callback_class`.
2. Add the necessary members and methods to customize your application's behavior.

---

## Define the Callback Function

1. Inside your callback class, define a callback function.
2. This function will handle data from the pipeline and can include your custom logic.

---

## Modify the Main Function

1. Update the `main` function to initialize and run your application.
2. Replace `GStreamerDetectionApp` with the appropriate GStreamer application for your use case.

This structure ensures your project can run as a standalone script.

---

## Adding New Pipelines

If your project requires a new pipeline:

1. Use the existing pipelines as references.
2. **You must inherit** from the `GStreamerApp` template class for consistency and maintainability.
3. Note: We may consider incorporating your pipeline into the core codebase if it is generic, well-tested, and addresses a broader need.

---

# Not Using Basic Pipelines as a Template

Basic Pipelines are optimized for high performance and frame rates. However, there are scenarios where you might prefer an alternative approach, here are some examples:

- Running a single inference job on demand for a specific service.
- Switching between multiple networks and tasks dynamically.
- Using special preprocessing stages or data types unsupported by Basic Pipelines.
  - Our pipelines leverage GStreamer, which is built for video and audio data. For more information, refer to the [GStreamer documentation](https://gstreamer.freedesktop.org/documentation/).

We encourage projects that explore alternative approaches. We will add our 'native' examples as well
If your project does not use Basic Pipelines, please ensure you include comprehensive documentation and installation instructions.

---

## Adding New Networks and Post-Processes

We are working on a "Community Model Zoo" to allow users to share models and post-processes on our servers. Meanwhile, follow these steps:

1. Save your HEF file on a file-sharing service like Google Drive.
2. Provide a `download_resources.sh` script to automate the download.
3. If you develop a new post-process:
   - Add the necessary code and a compilation script.
   - Refer to the [Hailo Apps Infra repository](https://github.com/hailo-ai/hailo-apps-infra) for guidance on creating and compiling new post-processes.

---

## Update Project Files
See the template example [README.md](./temaplate_example/README.md) for guidance on updating your project files.

---

# Pull Requests (PRs)

To contribute your project or improvements:

1. Submit a PR to the **`dev` branch** of the repository.
2. Your code should remain within your `community_projects/<your_project_name>` directory. **PRs modifying core code will be rejected.**
3. If you must alter core code for your project:
   - Copy the relevant code into your directory and modify it as needed.
   - Alternatively, suggest manual edits in your instructions.
   - **Be aware**: This approach may cause compatibility issues in future releases due to lack of backward compatibility. Breaking your code.

Suggestions for improving the core codebase are welcome. However, they must be generic, well-tested, and adaptable to multiple platforms.
If you identify missing functionality in our framework, you are welcome to implement it in your project directory. Exceptional features or common functions might be integrated into our core codebase.
**Important:** Code added to the core must meet these requirements:
- Thoroughly tested and verified.
- Generic and adaptable to multiple platforms.

By adhering to these guidelines, you help maintain the repository's stability and enable better integration of your work.

---

# Important Guidelines

### **Do Not Add Binary Files**
- Avoid adding non-code files (e.g., images, HEFs, videos) directly to the repository.
- Use a `download_resources.sh` script to fetch these files from external sources like Google Drive.
- For Model Zoo HEFs, download them directly from Hailo's servers.
## Code of Conduct

We are committed to fostering a welcoming and inclusive community. Please ensure that your contributions adhere to the following guidelines:

- Use clean and non-offensive language.
- Be respectful and considerate of others.
- Avoid any form of harassment or discrimination.

---