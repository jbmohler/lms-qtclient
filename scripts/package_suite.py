import os
import argparse
import rtxsite
import pkgscripts.package as package

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Package fido Suite")
    parser.add_argument(
        "--view",
        "-v",
        default=False,
        action="store_true",
        help="view build directory after build",
    )
    args = parser.parse_args()

    outroot = package.main()

    if args.view:
        os.startfile(outroot)
