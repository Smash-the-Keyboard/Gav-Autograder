FROM gav-autograder/base
# Add files for testing
COPY student-program /testspace
COPY input-file-*.txt /testspace/