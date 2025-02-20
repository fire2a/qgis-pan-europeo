#!/bin/bash

# Find all symbolic links in the repository
find . -type l | while read -r symlink; do
    # Get the target of the symbolic link
    target=$(readlink "$symlink")
    
    # Remove the symbolic link
    rm "$symlink"
    
    # Copy the target file to the location of the symbolic link
    cp "$target" "$symlink"
done