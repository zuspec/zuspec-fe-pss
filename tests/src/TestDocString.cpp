/*
 * TestDocString.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include "MarkerCollector.h"
#include "TestDocString.h"


namespace zsp {
namespace parser {




TestDocString::TestDocString() {

}

TestDocString::~TestDocString() {

}

TEST_F(TestDocString, DISABLED_smoke) {
    const char *text = R"(
        /**
         * This is a docstring
         * 
         */
        struct myStruct {

        }
    )";


    MarkerCollector marker_c;
    ast::IGlobalScopeUP root(parse(&marker_c, text, "smoke.pss", true));
    ASSERT_TRUE(root.get());
    ASSERT_FALSE(marker_c.hasSeverity(MarkerSeverityE::Error));
    ASSERT_EQ(root->getChildren().size(), 1);
    ast::IStruct *s = dynamic_cast<ast::IStruct *>(root->getChildren().at(0).get());
    ASSERT_TRUE(s);
    ASSERT_NE(s->getDocstring(), "");
}

TEST_F(TestDocString, DISABLED_smoke2) {
    const char *text = R"(
        //
        // This is a docstring
        // 
        //
        struct myStruct {

        }
    )";


    MarkerCollector marker_c;
    ast::IGlobalScopeUP root(parse(&marker_c, text, "smoke.pss", true));
    ASSERT_TRUE(root.get());
    ASSERT_FALSE(marker_c.hasSeverity(MarkerSeverityE::Error));
    ASSERT_EQ(root->getChildren().size(), 1);
    ast::IStruct *s = dynamic_cast<ast::IStruct *>(root->getChildren().at(0).get());
    ASSERT_TRUE(s);
    ASSERT_NE(s->getDocstring(), "");
}

}
}
